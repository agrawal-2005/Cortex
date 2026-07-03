"""Query API route — natural language question → best matching skill."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.knowledge.models import (
    Document,
    Skill,
    SkillDocument,
    SkillStep,
    StepSource,
)
from backend.processing.embedder import COLLECTION_NAME as DOC_COLLECTION
from backend.processing.embeddings import EmbeddingService
from backend.processing.renderer import render_skill_plain
from backend.schemas import (
    MatchedDocument,
    QueryRequest,
    QueryResponse,
    QuerySourceHit,
    SkillResponse,
)
from backend.vectorstore.store import VectorStore

router = APIRouter(tags=["query"])

_embedding_service = EmbeddingService()
# Search DOCUMENT embeddings (cortex_documents) — all ingesters write there.
_vector_store = VectorStore(collection_name=DOC_COLLECTION)

# Minimum relevance score (0-1) for a document to be considered a match.
# Below this threshold, results are treated as "no match found".
# Relevance equals cosine similarity (see distance conversion below), so
# 0.25 keeps topically related hits and drops incidental word overlap.
_RELEVANCE_THRESHOLD = 0.25

_NO_MATCH_RESPONSE = (
    "I don't have enough knowledge to answer that question yet. "
    "Try ingesting more documents related to this topic, or rephrase your question."
)


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
            readable_answer=_NO_MATCH_RESPONSE,
        )

    # 3. Score and filter hits by relevance threshold
    doc_relevance: dict[str, float] = {}
    source_hits: list[QuerySourceHit] = []

    for hit in hits:
        meta = hit.get("metadata", {})
        doc_id = meta.get("document_id") or hit.get("id", "").removeprefix("doc-")
        distance = hit.get("distance", 2.0)
        # The collection uses ChromaDB's default squared-L2 metric and our
        # embeddings are unit-normalized, so d = 2 - 2*cos_sim. Convert back:
        # relevance = 1 - d/2 = cosine similarity (clamped to [0, 1]).
        relevance = max(0.0, 1.0 - distance / 2.0)
        doc_text = hit.get("document", "")

        # Skip low-relevance results
        if relevance < _RELEVANCE_THRESHOLD:
            continue

        if doc_id:
            doc_relevance[doc_id] = max(doc_relevance.get(doc_id, 0.0), relevance)
            source_hits.append(
                QuerySourceHit(
                    document_id=doc_id,
                    content_snippet=doc_text[:200] if doc_text else "",
                    source_type=meta.get("source_type", "unknown"),
                    relevance=round(relevance, 3),
                )
            )

    # No documents passed the relevance threshold
    if not doc_relevance:
        return QueryResponse(
            question=question,
            readable_answer=_NO_MATCH_RESPONSE,
        )

    # 4. Map the matched documents back to the skill extracted from
    #    their cluster (skill_documents), falling back to LLM citations.
    skill = await _find_best_skill(db, doc_relevance)

    if skill is None:
        matched = await _matched_documents(db, doc_relevance)
        return QueryResponse(
            question=question,
            readable_answer=(
                "No structured workflow has been extracted for this topic "
                "yet. However, I found relevant source documents:"
            ),
            source_hits=source_hits[:5],
            matched_documents=matched,
            suggestion=(
                "Run skill extraction to generate a structured workflow "
                "from these documents."
            ),
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


async def _matched_documents(
    db: AsyncSession, doc_relevance: dict[str, float]
) -> list[MatchedDocument]:
    """Load the matched Document rows to expose source_link / author,
    which the vector-store hit metadata does not carry."""
    result = await db.execute(
        select(Document).where(Document.id.in_(doc_relevance.keys()))
    )
    docs = result.scalars().all()
    matched = [
        MatchedDocument(
            content_preview=(doc.content or "")[:200],
            source_type=doc.source_type,
            source_link=doc.source_link,
            author=doc.author_name,
            relevance=round(doc_relevance.get(doc.id, 0.0), 3),
        )
        for doc in docs
    ]
    matched.sort(key=lambda m: m.relevance, reverse=True)
    return matched[:5]


async def _find_best_skill(
    db: AsyncSession, doc_relevance: dict[str, float]
) -> Skill | None:
    """Find the skill whose source cluster best matches the given documents.

    Primary lookup: skill_documents — cluster-level provenance written at
    extraction time, linking EVERY document of the source cluster to its
    skill. Ranked by the highest-relevance matching document (so a skill
    with one strong match beats a large cluster with several weak ones),
    tie-broken by total relevance, then skill confidence.

    Fallback: step_sources — the handful of documents the LLM explicitly
    cited. Covers legacy skills extracted before skill_documents existed.
    """
    if not doc_relevance:
        return None

    doc_ids = list(doc_relevance)

    # ── Primary: cluster provenance (skill_documents) ──────────────────
    result = await db.execute(
        select(SkillDocument.skill_id, SkillDocument.document_id)
        .where(SkillDocument.document_id.in_(doc_ids))
    )
    max_rel: dict[str, float] = {}
    sum_rel: dict[str, float] = {}
    for skill_id, doc_id in result.all():
        rel = doc_relevance.get(doc_id, 0.0)
        max_rel[skill_id] = max(max_rel.get(skill_id, 0.0), rel)
        sum_rel[skill_id] = sum_rel.get(skill_id, 0.0) + rel

    if max_rel:
        result = await db.execute(
            select(Skill)
            .options(selectinload(Skill.steps).selectinload(SkillStep.sources))
            .where(Skill.id.in_(max_rel.keys()))
        )
        skills = result.scalars().all()
        if skills:
            return max(
                skills,
                key=lambda s: (
                    max_rel.get(s.id, 0.0),
                    sum_rel.get(s.id, 0.0),
                    s.confidence,
                ),
            )

    # ── Fallback: LLM-cited step_sources (legacy skills) ────────────────
    result = await db.execute(
        select(StepSource.step_id)
        .where(StepSource.document_id.in_(doc_ids))
        .distinct()
    )
    step_ids = [row[0] for row in result.all()]

    if not step_ids:
        return None

    result = await db.execute(
        select(SkillStep.skill_id)
        .where(SkillStep.id.in_(step_ids))
        .distinct()
    )
    skill_ids = [row[0] for row in result.all()]

    if not skill_ids:
        return None

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
