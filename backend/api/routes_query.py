"""Query API route — natural language question → best matching skill."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.knowledge.models import Skill, SkillStep, StepSource
from backend.processing.embeddings import EmbeddingService
from backend.processing.renderer import render_skill_plain
from backend.schemas import QueryRequest, QueryResponse, QuerySourceHit, SkillResponse
from backend.vectorstore.store import VectorStore

router = APIRouter(tags=["query"])

_embedding_service = EmbeddingService()
_vector_store = VectorStore()


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Ask a natural language question",
    description=(
        'Submit a question like "How do we handle refunds?" and get '
        "the best matching skill with source citations and a "
        "human-readable answer."
    ),
)
async def query_knowledge(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")

    # 1. Embed the question
    query_embedding = _embedding_service.generate_embedding(question)

    # 2. Search ChromaDB for similar documents
    hits = _vector_store.search(query_embedding, n_results=10)

    if not hits:
        return QueryResponse(
            question=question,
            readable_answer="No matching knowledge found for your question.",
        )

    # 3. Collect document IDs from vector-search hits
    doc_ids: list[str] = []
    source_hits: list[QuerySourceHit] = []

    for hit in hits:
        meta = hit.get("metadata", {})
        doc_id = meta.get("document_id") or hit.get("id", "").removeprefix("doc-")
        distance = hit.get("distance", 1.0)
        relevance = max(0.0, 1.0 - distance)  # cosine distance → relevance
        doc_text = hit.get("document", "")

        if doc_id:
            doc_ids.append(doc_id)
            source_hits.append(
                QuerySourceHit(
                    document_id=doc_id,
                    content_snippet=doc_text[:200] if doc_text else "",
                    source_type=meta.get("source_type", "unknown"),
                    relevance=round(relevance, 3),
                )
            )

    # 4. Find skills whose steps cite any of these documents
    skill = await _find_best_skill(db, doc_ids)

    if skill is None:
        return QueryResponse(
            question=question,
            readable_answer=(
                "Found related documents but no extracted skill yet. "
                "Run the extraction pipeline on these documents."
            ),
            source_hits=source_hits[:5],
        )

    # 5. Build response
    readable = render_skill_plain(skill)
    skill_response = SkillResponse.model_validate(skill)

    return QueryResponse(
        question=question,
        skill=skill_response,
        readable_answer=readable,
        source_hits=source_hits[:5],
        confidence=skill.confidence,
    )


async def _find_best_skill(
    db: AsyncSession, doc_ids: list[str]
) -> Skill | None:
    """Find the skill with the most step-source citations to the given documents."""
    if not doc_ids:
        return None

    # Find step_sources that reference our documents
    result = await db.execute(
        select(StepSource.step_id)
        .where(StepSource.document_id.in_(doc_ids))
        .distinct()
    )
    step_ids = [row[0] for row in result.all()]

    if not step_ids:
        return None

    # Find the skill(s) that own these steps
    result = await db.execute(
        select(SkillStep.skill_id)
        .where(SkillStep.id.in_(step_ids))
        .distinct()
    )
    skill_ids = [row[0] for row in result.all()]

    if not skill_ids:
        return None

    # Load the highest-confidence skill
    result = await db.execute(
        select(Skill)
        .options(
            selectinload(Skill.steps).selectinload(SkillStep.sources)
        )
        .where(Skill.id.in_(skill_ids))
        .order_by(Skill.confidence.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
