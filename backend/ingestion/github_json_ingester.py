"""GitHub JSON export ingester.

Parses a GitHub export shaped as ``{"repo": "...", "items": [...]}``
(or a bare list of items) where each item mirrors the GitHub REST API
issue shape: number, title, body, state, user.login, created_at,
labels, comments (list of ``{user: {login}, body, created_at}``), and —
for pull requests — a ``pull_request`` key (with ``merged_at``).

Each item becomes one Cortex ``DocumentCreate`` with
``source_type="github_pr"`` or ``"github_issue"``, matching the format
produced by the live :class:`GitHubIngester` so extraction treats
static exports and API pulls identically.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.schemas import DocumentCreate

logger = logging.getLogger(__name__)

DEFAULT_REPO = "acmetech/platform"


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # DB column is TIMESTAMP WITHOUT TIME ZONE — store naive UTC.
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


class GitHubJsonIngester:
    """Converts a GitHub JSON export into DocumentCreate records."""

    def __init__(self) -> None:
        self.stats = {"prs": 0, "issues": 0, "comments": 0, "skipped": 0}

    def _item_to_document(
        self, item: dict[str, Any], repo: str
    ) -> DocumentCreate | None:
        number = item.get("number")
        title = item.get("title", "")
        if not number or not title:
            self.stats["skipped"] += 1
            return None

        is_pr = "pull_request" in item
        kind = "PR" if is_pr else "Issue"
        parts = [f"{kind} #{number}: {title}"]

        meta = [f"State: {item['state']}"] if item.get("state") else []
        labels = [
            lbl.get("name") if isinstance(lbl, dict) else lbl
            for lbl in item.get("labels") or []
        ]
        if labels:
            meta.append("Labels: " + ", ".join(str(l) for l in labels if l))
        if meta:
            parts.append(" | ".join(meta))

        body = (item.get("body") or "").strip()
        if body:
            parts.append(body)

        comment_lines = []
        for comment in item.get("comments") or []:
            if not isinstance(comment, dict):
                continue
            c_body = (comment.get("body") or "").strip()
            if not c_body:
                continue
            author = (comment.get("user") or {}).get("login", "unknown")
            comment_lines.append(f"[{author}]: {c_body}")
            self.stats["comments"] += 1
        if comment_lines:
            parts.append("--- Comments ---\n\n" + "\n\n".join(comment_lines))

        self.stats["prs" if is_pr else "issues"] += 1
        path = "pull" if is_pr else "issues"
        return DocumentCreate(
            content="\n\n".join(parts),
            source_type="github_pr" if is_pr else "github_issue",
            source_id=f"{repo}#{number}",
            source_link=item.get("html_url")
            or f"https://github.com/{repo}/{path}/{number}",
            source_label=f"{repo} {kind.lower()} #{number}",
            channel_or_project=repo,
            author_name=(item.get("user") or {}).get("login"),
            created_at=_parse_timestamp(item.get("created_at")),
        )

    async def parse_export(self, data: Any) -> list[DocumentCreate]:
        """Parse a GitHub export (``{"items": [...]}`` or a bare list)."""
        repo = DEFAULT_REPO
        if isinstance(data, dict):
            items = data.get("items")
            repo = data.get("repo") or repo
        elif isinstance(data, list):
            items = data
        else:
            items = None
        if not isinstance(items, list):
            raise ValueError(
                "Expected a GitHub export with an 'items' array "
                "(or a bare JSON array of PRs/issues)."
            )

        docs: list[DocumentCreate] = []
        for item in items:
            if not isinstance(item, dict):
                self.stats["skipped"] += 1
                continue
            doc = self._item_to_document(item, repo)
            if doc:
                docs.append(doc)
        logger.info("Parsed GitHub export: %s", self.stats)
        return docs
