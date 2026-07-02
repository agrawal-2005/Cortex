"""Celery tasks for data ingestion from external sources."""

import asyncio
import logging
from typing import Any

from backend.tasks.worker import app
from backend.database import AsyncSessionLocal
from backend.models import Document

logger = logging.getLogger(__name__)


@app.task(bind=True, name="cortex.ingest_from_slack", max_retries=3)
def ingest_from_slack(self: Any, channel_id: str, bot_token: str) -> dict[str, Any]:
    """Ingest documents from a Slack channel.

    Creates a SlackConnector, fetches messages/threads, saves them as
    documents in the database, and triggers the processing pipeline.

    Args:
        channel_id: The Slack channel ID to fetch from.
        bot_token: The Slack bot token for authentication.

    Returns:
        Dict with status and document count.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _async_ingest_from_slack(channel_id, bot_token)
        )
        return result
    except Exception as exc:
        logger.error("Slack ingestion failed for channel %s: %s", channel_id, exc)
        raise self.retry(exc=exc, countdown=60)
    finally:
        loop.close()


async def _async_ingest_from_slack(
    channel_id: str, bot_token: str
) -> dict[str, Any]:
    """Async implementation of Slack ingestion."""
    from backend.ingestion.slack_connector import SlackConnector

    connector = SlackConnector(bot_token=bot_token)
    raw_documents = await connector.fetch_documents(channel_id=channel_id)

    document_ids: list[str] = []

    async with AsyncSessionLocal() as db:
        for doc_data in raw_documents:
            document = Document(
                title=doc_data.get("title", f"Slack message from #{channel_id}"),
                content=doc_data.get("content", ""),
                source_type="slack",
                source_id=doc_data.get("source_id", channel_id),
                metadata=doc_data.get("metadata", {}),
            )
            db.add(document)
            await db.flush()
            document_ids.append(str(document.id))

        await db.commit()

    # Trigger processing pipeline
    if document_ids:
        from backend.tasks.processing_tasks import process_documents

        process_documents.delay(document_ids)

    logger.info(
        "Ingested %d documents from Slack channel %s",
        len(document_ids),
        channel_id,
    )

    return {
        "status": "completed",
        "channel_id": channel_id,
        "document_count": len(document_ids),
        "document_ids": document_ids,
    }
