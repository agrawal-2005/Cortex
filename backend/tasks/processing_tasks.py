"""Celery tasks for document processing and skill extraction."""

import asyncio
import logging
from typing import Any

from backend.tasks.worker import app
from backend.database import AsyncSessionLocal
from backend.models import Skill

logger = logging.getLogger(__name__)


@app.task(bind=True, name="cortex.process_documents", max_retries=2)
def process_documents(
    self: Any, document_ids: list[str]
) -> dict[str, Any]:
    """Process documents through the extraction pipeline.

    Creates a ProcessingPipeline, extracts skills from the given documents,
    generates embeddings, and stores results.

    Args:
        document_ids: List of document IDs to process.

    Returns:
        Dict with status and list of created skill IDs.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _async_process_documents(document_ids)
        )
        return result
    except Exception as exc:
        logger.error("Document processing failed: %s", exc)
        raise self.retry(exc=exc, countdown=120)
    finally:
        loop.close()


async def _async_process_documents(
    document_ids: list[str],
) -> dict[str, Any]:
    """Async implementation of document processing."""
    from backend.processing.pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline()
    skill_ids = await pipeline.process_documents(document_ids)

    return {
        "status": "completed",
        "document_ids": document_ids,
        "skill_ids": skill_ids,
        "skills_created": len(skill_ids),
    }


@app.task(bind=True, name="cortex.reprocess_skill", max_retries=2)
def reprocess_skill(self: Any, skill_id: str) -> dict[str, Any]:
    """Re-extract a skill from its original source documents.

    Fetches the skill's source_document_ids and runs them back through
    the processing pipeline.

    Args:
        skill_id: The ID of the skill to reprocess.

    Returns:
        Dict with status and new skill IDs.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_async_reprocess_skill(skill_id))
        return result
    except Exception as exc:
        logger.error("Skill reprocessing failed for %s: %s", skill_id, exc)
        raise self.retry(exc=exc, countdown=120)
    finally:
        loop.close()


async def _async_reprocess_skill(skill_id: str) -> dict[str, Any]:
    """Async implementation of skill reprocessing."""
    from backend.processing.pipeline import ProcessingPipeline
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Skill).where(Skill.id == skill_id))
        skill = result.scalar_one_or_none()

        if skill is None:
            return {
                "status": "error",
                "skill_id": skill_id,
                "message": "Skill not found",
            }

        source_document_ids: list[str] = (
            skill.source_document_ids
            if isinstance(skill.source_document_ids, list)
            else []
        )

        if not source_document_ids:
            return {
                "status": "error",
                "skill_id": skill_id,
                "message": "No source documents linked to this skill",
            }

    # Reprocess through the pipeline
    pipeline = ProcessingPipeline()
    new_skill_ids = await pipeline.process_documents(source_document_ids)

    return {
        "status": "completed",
        "original_skill_id": skill_id,
        "new_skill_ids": new_skill_ids,
        "skills_created": len(new_skill_ids),
    }
