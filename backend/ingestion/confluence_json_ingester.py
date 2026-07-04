"""Confluence JSON export ingester.

Parses a Confluence export shaped as ``{"pages": [...]}`` (or a bare
list of pages) where each page has: id, title, space, body, author,
created, last_modified, url.

Each page becomes one Cortex ``DocumentCreate`` with
``source_type="confluence"``. ``created_at`` uses ``last_modified`` so
recency-based conflict resolution sees when the page content was last
touched, not when the page was first created.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.schemas import DocumentCreate

logger = logging.getLogger(__name__)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # DB column is TIMESTAMP WITHOUT TIME ZONE — store naive UTC.
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


class ConfluenceJsonIngester:
    """Converts a Confluence JSON export into DocumentCreate records."""

    def __init__(self) -> None:
        self.stats = {"pages": 0, "skipped": 0}

    def _page_to_document(self, page: dict[str, Any]) -> DocumentCreate | None:
        page_id = str(page.get("id") or "")
        title = page.get("title", "")
        body = page.get("body", "")
        if not page_id or not title or not body:
            self.stats["skipped"] += 1
            return None

        parts = [title]
        if page.get("space"):
            parts.append(f"Space: {page['space']}")
        if page.get("last_modified"):
            parts.append(f"Last modified: {page['last_modified']}")
        parts.append(body)

        self.stats["pages"] += 1
        return DocumentCreate(
            content="\n\n".join(parts),
            source_type="confluence",
            source_id=page_id,
            source_link=page.get("url"),
            source_label=title,
            channel_or_project=page.get("space"),
            author_name=page.get("author"),
            created_at=_parse_timestamp(
                page.get("last_modified") or page.get("created")
            ),
        )

    async def parse_export(self, data: Any) -> list[DocumentCreate]:
        """Parse a Confluence export (``{"pages": [...]}`` or a bare list)."""
        if isinstance(data, dict):
            pages = data.get("pages")
        elif isinstance(data, list):
            pages = data
        else:
            pages = None
        if not isinstance(pages, list):
            raise ValueError(
                "Expected a Confluence export with a 'pages' array "
                "(or a bare JSON array of pages)."
            )

        docs: list[DocumentCreate] = []
        for page in pages:
            if not isinstance(page, dict):
                self.stats["skipped"] += 1
                continue
            doc = self._page_to_document(page)
            if doc:
                docs.append(doc)
        logger.info("Parsed Confluence export: %s", self.stats)
        return docs
