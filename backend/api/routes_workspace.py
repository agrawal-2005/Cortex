"""Workspace data deletion — a real, verified hard delete.

DELETE /api/workspace/data removes everything Cortex has ingested or
derived: documents, skills (with steps/sources/provenance), pending
clusters, feedback, connected sources (including their encrypted
tokens), source-trust scores, and every vector in both ChromaDB
collections. Rows are physically deleted, not flagged.

API keys are deliberately kept — deleting them would lock the caller
out of the API mid-request.

The response includes a post-deletion verification: fresh row counts
per table and vector counts per collection, all of which must be zero
or the endpoint fails loudly instead of claiming success.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.knowledge.models import (
    ApiKey,
    ConnectedSource,
    Document,
    Feedback,
    PendingCluster,
    Skill,
    SkillDocument,
    SkillStep,
    SourceTrust,
    StepSource,
)
from backend.processing.embedder import COLLECTION_NAME as DOC_COLLECTION
from backend.security.auth import require_api_key
from backend.vectorstore.store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspace"])

CONFIRMATION_PHRASE = "DELETE"

# Children before parents so the cascade is explicit and does not depend
# on the database enforcing FK ON DELETE (SQLite in tests does not).
_DELETION_ORDER: list[tuple[str, type]] = [
    ("feedback", Feedback),
    ("step_sources", StepSource),
    ("skill_steps", SkillStep),
    ("skill_documents", SkillDocument),
    ("pending_clusters", PendingCluster),
    ("skills", Skill),
    ("documents", Document),
    ("connected_sources", ConnectedSource),
    ("source_trust", SourceTrust),
]


class DeleteWorkspaceRequest(BaseModel):
    confirm: str


async def _table_counts(db: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, model in _DELETION_ORDER:
        counts[name] = (
            await db.execute(select(func.count()).select_from(model))
        ).scalar() or 0
    return counts


@router.delete(
    "/data",
    summary="Delete ALL workspace data (irreversible)",
    description=(
        "Hard-deletes every document, skill, pending topic, feedback "
        "entry, connected source (and its stored token), trust score, "
        "and vector embedding. Requires {\"confirm\": \"DELETE\"} in the "
        "request body. API keys are kept so access is not lost. "
        "Verified after deletion — the response proves zero rows and "
        "zero vectors remain."
    ),
)
async def delete_workspace_data(
    body: DeleteWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(require_api_key),
) -> dict[str, Any]:
    if body.confirm != CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=400,
            detail=(
                f'Confirmation failed: send {{"confirm": "{CONFIRMATION_PHRASE}"}} '
                "to delete all workspace data."
            ),
        )

    # ── 1. Hard-delete Postgres rows, children first ──────────────────
    deleted = await _table_counts(db)
    for _, model in _DELETION_ORDER:
        await db.execute(delete(model))
    await db.flush()

    # ── 2. Wipe both ChromaDB collections (document + skill vectors) ──
    deleted["document_vectors"] = VectorStore(collection_name=DOC_COLLECTION).clear()
    deleted["skill_vectors"] = VectorStore().clear()  # cortex_skills

    # ── 3. Verify: zero rows, zero vectors ────────────────────────────
    verified = await _table_counts(db)
    verified["document_vectors"] = VectorStore(
        collection_name=DOC_COLLECTION
    ).get_collection_stats()["count"]
    verified["skill_vectors"] = VectorStore().get_collection_stats()["count"]

    leftovers = {k: v for k, v in verified.items() if v != 0}
    if leftovers:
        # Fail loudly (rolls back the transaction) rather than telling
        # the caller their data is gone when it is not.
        logger.error("Workspace deletion left data behind: %s", leftovers)
        raise HTTPException(
            status_code=500,
            detail=f"Deletion incomplete, transaction rolled back: {leftovers}",
        )

    # ── 4. Log the deletion event ──────────────────────────────────────
    deleted_at = datetime.now(timezone.utc).isoformat()
    logger.warning(
        "WORKSPACE FULLY DELETED at %s by API key '%s' (prefix %s) — removed: %s",
        deleted_at,
        api_key.name,
        api_key.prefix,
        deleted,
    )

    return {
        "status": "deleted",
        "deleted": deleted,
        "verified_remaining": verified,
        "deleted_at": deleted_at,
        "triggered_by": {"api_key_name": api_key.name, "api_key_prefix": api_key.prefix},
    }
