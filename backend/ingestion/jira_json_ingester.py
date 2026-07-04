"""Jira JSON export ingester.

Parses a Jira export shaped as ``{"issues": [...]}`` (or a bare list of
issues) where each issue has: key, summary, description, status,
issue_type, priority, assignee, reporter, created, updated, comments
(list of ``{author, body, created}``), labels, resolution.

Each issue becomes one Cortex ``DocumentCreate`` with
``source_type="jira"``. The content concatenates the summary,
description, and all comments (with authors and timestamps) so the full
discussion is available for skill extraction.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.schemas import DocumentCreate

logger = logging.getLogger(__name__)

JIRA_BASE_URL = "https://acmetech.atlassian.net/browse"


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # DB column is TIMESTAMP WITHOUT TIME ZONE — store naive UTC.
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


class JiraJsonIngester:
    """Converts a Jira JSON export into DocumentCreate records."""

    def __init__(self) -> None:
        self.stats = {"issues": 0, "comments": 0, "skipped": 0}

    def _issue_to_document(self, issue: dict[str, Any]) -> DocumentCreate | None:
        key = issue.get("key")
        summary = issue.get("summary", "")
        if not key or not summary:
            self.stats["skipped"] += 1
            return None

        parts = [f"[{key}] {summary}"]

        meta = " | ".join(
            f"{label}: {issue[field]}"
            for label, field in (
                ("Type", "issue_type"),
                ("Priority", "priority"),
                ("Status", "status"),
                ("Assignee", "assignee"),
                ("Reporter", "reporter"),
            )
            if issue.get(field)
        )
        if meta:
            parts.append(meta)

        labels = issue.get("labels") or []
        if labels:
            parts.append("Labels: " + ", ".join(labels))
        if issue.get("resolution"):
            parts.append(f"Resolution: {issue['resolution']}")

        if issue.get("description"):
            parts.append(issue["description"])

        for comment in issue.get("comments") or []:
            body = comment.get("body", "").strip()
            if not body:
                continue
            author = comment.get("author", "unknown")
            created = comment.get("created", "")
            parts.append(f"Comment by {author} ({created}):\n{body}")
            self.stats["comments"] += 1

        self.stats["issues"] += 1
        return DocumentCreate(
            content="\n\n".join(parts),
            source_type="jira",
            source_id=key,
            source_link=f"{JIRA_BASE_URL}/{key}",
            source_label=key,
            channel_or_project=key.split("-")[0],
            author_name=issue.get("reporter"),
            created_at=_parse_timestamp(issue.get("updated") or issue.get("created")),
        )

    async def parse_export(self, data: Any) -> list[DocumentCreate]:
        """Parse a Jira export (``{"issues": [...]}`` or a bare list)."""
        if isinstance(data, dict):
            issues = data.get("issues")
        elif isinstance(data, list):
            issues = data
        else:
            issues = None
        if not isinstance(issues, list):
            raise ValueError(
                "Expected a Jira export with an 'issues' array "
                "(or a bare JSON array of issues)."
            )

        docs: list[DocumentCreate] = []
        for issue in issues:
            if not isinstance(issue, dict):
                self.stats["skipped"] += 1
                continue
            doc = self._issue_to_document(issue)
            if doc:
                docs.append(doc)
        logger.info("Parsed Jira export: %s", self.stats)
        return docs
