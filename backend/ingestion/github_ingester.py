"""GitHub repository ingester.

Pulls issues, pull requests, discussions, and docs from a public GitHub
repository via the REST API and converts them into Cortex documents.

No auth token is required for public repos, but the unauthenticated rate
limit is 60 requests/hour, so this ingester tracks a request budget and
stops gracefully when it is exhausted. Pass a token (or set GITHUB_TOKEN)
to raise the limit to 5000 requests/hour.
"""

import asyncio
import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.ingestion.base import BaseConnector
from backend.schemas import DocumentCreate

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"

# Doc files to look for at the repo root (and .github/ for CONTRIBUTING).
ROOT_DOC_FILES = ["README.md", "CONTRIBUTING.md", ".github/CONTRIBUTING.md"]
DOC_EXTENSIONS = (".md", ".mdx", ".rst", ".txt")


class RateLimitExhausted(Exception):
    """Raised internally when the GitHub API request budget is used up."""


class GitHubIngester(BaseConnector):
    """Ingests issues, PRs, discussions, and docs from a public GitHub repo."""

    def __init__(
        self,
        repo: str,
        token: str | None = None,
        months: int = 6,
        max_requests: int | None = None,
        include_comments: bool = True,
        max_doc_files: int = 30,
    ) -> None:
        """
        Args:
            repo: Repository in "owner/repo" form, e.g. "fastapi/fastapi".
            token: Optional GitHub token (falls back to GITHUB_TOKEN env var).
            months: How far back to pull issues/PRs (by last update).
            max_requests: API request budget; ingestion stops when exhausted.
                Defaults to 55 unauthenticated (60/hr limit) or 4000 with a
                token (5000/hr limit).
            include_comments: Fetch issue comments / PR review comments
                (one extra request per item — expensive on the 60/hr limit).
            max_doc_files: Cap on files pulled from the docs/ folder.
        """
        if "/" not in repo:
            raise ValueError(f"repo must be in 'owner/repo' form, got: {repo!r}")
        self.repo = repo
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.since = datetime.now(timezone.utc) - timedelta(days=months * 30)
        self.max_requests = max_requests or (4000 if self.token else 55)
        self.include_comments = include_comments
        self.max_doc_files = max_doc_files
        self._client: httpx.AsyncClient | None = None
        self._requests_used = 0
        self.stats = {
            "issues": 0,
            "prs": 0,
            "discussions": 0,
            "docs": 0,
            "requests_used": 0,
            "rate_limited": False,
        }

    async def connect(self) -> None:
        """Create the HTTP client and verify the repo exists."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cortex-ingester",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE, headers=headers, timeout=30.0
        )
        resp = await self._get(f"/repos/{self.repo}")
        if resp is None:
            raise ConnectionError(f"Cannot reach GitHub repo: {self.repo}")
        logger.info("Connected to GitHub repo %s", self.repo)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response | None:
        """GET with budget tracking and rate-limit handling.

        Returns None for 404s (missing/disabled resources).
        Raises RateLimitExhausted when the budget or API limit is hit.
        """
        assert self._client is not None, "Call connect() first"
        if self._requests_used >= self.max_requests:
            raise RateLimitExhausted(
                f"Request budget of {self.max_requests} exhausted"
            )

        resp = await self._client.get(path, params=params)
        self._requests_used += 1
        self.stats["requests_used"] = self._requests_used

        if resp.status_code == 404:
            return None
        if resp.status_code in (403, 429):
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining == "0":
                reset = resp.headers.get("X-RateLimit-Reset", "?")
                raise RateLimitExhausted(
                    f"GitHub rate limit hit (resets at epoch {reset})"
                )
        resp.raise_for_status()
        return resp

    async def _paginate(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all pages of a list endpoint."""
        items: list[dict[str, Any]] = []
        params = dict(params or {})
        params.setdefault("per_page", 100)
        page = 1
        while True:
            params["page"] = page
            try:
                resp = await self._get(path, params=params)
            except httpx.HTTPStatusError as e:
                # GitHub returns 422 when paginating past its result cap.
                if e.response.status_code == 422:
                    logger.info("Pagination cap reached for %s at page %d", path, page)
                    break
                raise
            except RateLimitExhausted:
                # Keep the pages we already have instead of losing them.
                self.stats["rate_limited"] = True
                logger.warning(
                    "Rate limit hit paginating %s at page %d; keeping %d items",
                    path, page, len(items),
                )
                break
            if resp is None:
                break
            batch = resp.json()
            if not batch:
                break
            items.extend(batch)
            if "next" not in resp.headers.get("Link", ""):
                break
            page += 1
        return items

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        # DB column is TIMESTAMP WITHOUT TIME ZONE — store naive UTC.
        return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt

    @staticmethod
    def _author(item: dict[str, Any]) -> str | None:
        user = item.get("user") or item.get("author") or {}
        return user.get("login")

    def _format_comments(self, comments: list[dict[str, Any]]) -> str:
        lines = []
        for c in comments:
            author = self._author(c) or "unknown"
            body = (c.get("body") or "").strip()
            if body:
                lines.append(f"[{author}]: {body}")
        return "\n\n".join(lines)

    # --- Issues and PRs ---

    async def _fetch_issues_and_prs(self) -> list[DocumentCreate]:
        """Fetch issues and PRs updated in the time window.

        The /issues endpoint returns both issues and PRs (PRs carry a
        "pull_request" key), so one paginated call covers both lists.
        """
        items = await self._paginate(
            f"/repos/{self.repo}/issues",
            params={
                "state": "all",
                "since": self.since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "updated",
                "direction": "desc",
            },
        )
        docs: list[DocumentCreate] = []
        for item in items:
            is_pr = "pull_request" in item
            number = item["number"]
            title = item.get("title", "")
            body = (item.get("body") or "").strip()
            kind = "PR" if is_pr else "Issue"
            content = f"{kind} #{number}: {title}\n\n{body}".strip()

            if self.include_comments and not self.stats["rate_limited"]:
                try:
                    comment_text = await self._fetch_item_comments(number, is_pr)
                except RateLimitExhausted:
                    # Out of budget for comments — still keep every item's
                    # title/body, which are already in memory.
                    self.stats["rate_limited"] = True
                    comment_text = ""
                if comment_text:
                    content += f"\n\n--- Comments ---\n\n{comment_text}"

            docs.append(
                DocumentCreate(
                    content=content,
                    source_type="github_pr" if is_pr else "github_issue",
                    source_id=f"{self.repo}#{number}",
                    source_link=item.get("html_url"),
                    source_label=f"{self.repo} {kind.lower()} #{number}",
                    channel_or_project=self.repo,
                    author_name=self._author(item),
                    created_at=self._parse_dt(item.get("created_at")),
                )
            )
            self.stats["prs" if is_pr else "issues"] += 1
        return docs

    async def _fetch_item_comments(self, number: int, is_pr: bool) -> str:
        """Fetch discussion comments (and review comments for PRs)."""
        parts: list[str] = []
        resp = await self._get(f"/repos/{self.repo}/issues/{number}/comments")
        if resp is not None:
            parts.append(self._format_comments(resp.json()))
        if is_pr:
            resp = await self._get(f"/repos/{self.repo}/pulls/{number}/comments")
            if resp is not None:
                review_text = self._format_comments(resp.json())
                if review_text:
                    parts.append(f"--- Review comments ---\n\n{review_text}")
        return "\n\n".join(p for p in parts if p)

    # --- Discussions ---

    async def _fetch_discussions(self) -> list[DocumentCreate]:
        """Fetch discussions; returns [] if discussions are disabled (404)."""
        try:
            items = await self._paginate(f"/repos/{self.repo}/discussions")
        except httpx.HTTPStatusError as e:
            logger.info("Discussions unavailable for %s: %s", self.repo, e)
            return []
        docs: list[DocumentCreate] = []
        for item in items:
            created = self._parse_dt(item.get("created_at"))
            if created and created < self.since:
                continue
            number = item.get("number")
            title = item.get("title", "")
            body = (item.get("body") or "").strip()
            docs.append(
                DocumentCreate(
                    content=f"Discussion #{number}: {title}\n\n{body}".strip(),
                    source_type="github_discussion",
                    source_id=f"{self.repo}/discussions/{number}",
                    source_link=item.get("html_url"),
                    source_label=f"{self.repo} discussion #{number}",
                    channel_or_project=self.repo,
                    author_name=self._author(item),
                    created_at=created,
                )
            )
            self.stats["discussions"] += 1
        return docs

    # --- Docs (README, CONTRIBUTING, docs/) ---

    async def _fetch_file_content(self, path: str) -> str | None:
        """Fetch a file via the contents API, decoding base64."""
        resp = await self._get(f"/repos/{self.repo}/contents/{path}")
        if resp is None:
            return None
        data = resp.json()
        if isinstance(data, dict) and data.get("encoding") == "base64":
            try:
                return base64.b64decode(data.get("content", "")).decode(
                    "utf-8", errors="replace"
                )
            except Exception:  # malformed content
                return None
        return None

    def _doc_document(self, path: str, content: str) -> DocumentCreate:
        return DocumentCreate(
            content=f"{path}\n\n{content}",
            source_type="github_doc",
            source_id=f"{self.repo}/{path}",
            source_link=f"https://github.com/{self.repo}/blob/HEAD/{path}",
            source_label=f"{self.repo} {path}",
            channel_or_project=self.repo,
        )

    async def _fetch_docs(self) -> list[DocumentCreate]:
        docs: list[DocumentCreate] = []

        # README via the dedicated endpoint (finds README.rst etc. too)
        resp = await self._get(f"/repos/{self.repo}/readme")
        if resp is not None:
            data = resp.json()
            content = base64.b64decode(data.get("content", "")).decode(
                "utf-8", errors="replace"
            )
            docs.append(self._doc_document(data.get("path", "README.md"), content))
            self.stats["docs"] += 1

        # CONTRIBUTING.md (root, then .github/)
        for path in ("CONTRIBUTING.md", ".github/CONTRIBUTING.md"):
            content = await self._fetch_file_content(path)
            if content:
                docs.append(self._doc_document(path, content))
                self.stats["docs"] += 1
                break

        # docs/ folder (top level only, capped)
        resp = await self._get(f"/repos/{self.repo}/contents/docs")
        if resp is not None:
            entries = resp.json()
            if isinstance(entries, list):
                fetched = 0
                for entry in entries:
                    if fetched >= self.max_doc_files:
                        break
                    if entry.get("type") != "file":
                        continue
                    name = entry.get("name", "")
                    if not name.lower().endswith(DOC_EXTENSIONS):
                        continue
                    content = await self._fetch_file_content(entry["path"])
                    if content:
                        docs.append(self._doc_document(entry["path"], content))
                        self.stats["docs"] += 1
                        fetched += 1
        return docs

    # --- Main entry point ---

    async def fetch_documents(self) -> list[DocumentCreate]:
        """Fetch all documents, stopping gracefully if rate-limited."""
        documents: list[DocumentCreate] = []
        # Docs first: they are cheap and most valuable per request on the
        # 60/hr unauthenticated budget.
        for fetcher in (
            self._fetch_docs,
            self._fetch_issues_and_prs,
            self._fetch_discussions,
        ):
            try:
                documents.extend(await fetcher())
            except RateLimitExhausted as e:
                logger.warning(
                    "Stopping ingestion early (%s). Collected %d documents so far.",
                    e,
                    len(documents),
                )
                self.stats["rate_limited"] = True
                break
        logger.info("GitHub ingestion of %s complete: %s", self.repo, self.stats)
        return documents

    async def ingest(self) -> list[DocumentCreate]:
        try:
            return await super().ingest()
        finally:
            await self.close()


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    async def main() -> None:
        repo = sys.argv[1] if len(sys.argv) > 1 else "fastapi/fastapi"
        ingester = GitHubIngester(repo, max_requests=25, include_comments=False)
        docs = await ingester.ingest()
        print(f"\nFetched {len(docs)} documents from {repo}")
        print(f"Stats: {ingester.stats}\n")
        for doc in docs[:5]:
            print(f"- [{doc.source_type}] {doc.source_label}")
            print(f"  author={doc.author_name} created={doc.created_at}")
            print(f"  link={doc.source_link}")
            print(f"  content: {doc.content[:120]!r}\n")

    asyncio.run(main())
