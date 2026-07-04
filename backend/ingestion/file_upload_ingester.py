import csv
import io
import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.knowledge.models import Document
from backend.processing.embedder import DocumentEmbedder

logger = logging.getLogger(__name__)


class FileUploadIngester:
    """Ingests documents from CSV or JSON file uploads."""

    def __init__(self):
        self.embedder = DocumentEmbedder()

    async def ingest_json(
        self,
        file_content: str,
        source_type: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Ingest documents from a JSON string (array of objects).

        Each object should have at least 'content'. Optional:
        source_id, source_link, source_label, channel_or_project,
        author_name, author_role.
        """
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError as e:
            return {"status": "error", "detail": f"Invalid JSON: {e}"}

        if not isinstance(data, list):
            return {"status": "error", "detail": "JSON must be an array of objects"}

        return await self._ingest_records(data, source_type, db)

    async def ingest_csv(
        self,
        file_content: str,
        source_type: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Ingest documents from a CSV string.

        CSV must have a 'content' column. Optional columns:
        source_id, source_link, source_label, channel_or_project,
        author_name, author_role.
        """
        reader = csv.DictReader(io.StringIO(file_content))
        records = list(reader)
        return await self._ingest_records(records, source_type, db)

    async def _ingest_records(
        self,
        records: list[dict],
        source_type: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Process a list of record dicts into Documents with embeddings."""
        created_docs: list[Document] = []
        skipped = 0
        errors: list[str] = []

        for idx, record in enumerate(records):
            content = (record.get("content") or "").strip()
            if not content:
                errors.append(f"Row {idx + 1}: missing 'content' field")
                skipped += 1
                continue

            doc = Document(
                content=content,
                source_type=source_type,
                source_id=record.get("source_id", f"{source_type}-{idx}").strip() or f"{source_type}-{idx}",
                source_link=record.get("source_link") or None,
                source_label=record.get("source_label") or None,
                channel_or_project=record.get("channel_or_project") or None,
                author_name=record.get("author_name") or None,
                author_role=record.get("author_role") or None,
            )
            db.add(doc)
            created_docs.append(doc)

        if created_docs:
            await db.flush()
            for doc in created_docs:
                await db.refresh(doc)

            # Generate embeddings (stored in the cortex_documents collection)
            await self.embedder.embed_documents(
                db, document_ids=[d.id for d in created_docs]
            )

        return {
            "status": "success",
            "documents_created": len(created_docs),
            "skipped": skipped,
            "errors": errors,
        }
