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
    skill = await _find_best_skill(db, doc_relevance, query_embedding)

    if skill is None:
        matched = await _matched_documents(db, doc_relevance)
        # Vector hits can reference documents that no longer exist in the
        # database (stale embeddings). Without real documents to show,
        # "here are the most relevant documents:" would render nothing.
        if not matched:
            return QueryResponse(
                question=question,
                readable_answer=_NO_MATCH_RESPONSE,
            )
        return QueryResponse(
            question=question,
            readable_answer=(
                "No structured workflow exists for this topic yet. "
                "Here are the most relevant documents:"
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
            preview=(doc.content or "")[:200],
            source_type=doc.source_type,
            source_link=doc.source_link,
            author=doc.author_name,
            relevance=round(doc_relevance.get(doc.id, 0.0), 3),
        )
        for doc in docs
    ]
    matched.sort(key=lambda m: m.relevance, reverse=True)
    return matched[:5]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return dot / norm if norm else 0.0


async def _find_best_skill(
    db: AsyncSession,
    doc_relevance: dict[str, float],
    query_embedding: list[float],
) -> Skill | None:
    """Find the skill whose source documents best match the given hits.

    Candidate skills come from BOTH provenance tables, merged into one
    pool before ranking:
      - skill_documents — cluster-level provenance written at extraction
        time, linking EVERY document of the source cluster to its skill.
      - step_sources — the handful of documents the LLM explicitly cited.
        The only provenance for legacy skills extracted before
        skill_documents existed; merging (rather than falling back) lets a
        legacy skill that owns the MOST relevant hit beat a big cluster
        of weakly relevant ones.

    Ranking blends two signals equally:
      - the skill's own semantic similarity to the question (embedding
        of "name. description"), and
      - the highest-relevance matching document.
    Document overlap alone cannot disambiguate: a skill owning one
    slightly-stronger incidental hit would beat the skill that is
    plainly *about* the question but whose docs score marginally lower
    (e.g. "report vulnerabilities?" hitting a TUI-dialog PR at 0.51 vs
    the pentest-report cluster at 0.47). Ties break on total relevance,
    then confidence.
    """
    if not doc_relevance:
        return None

    doc_ids = list(doc_relevance)

    pairs: set[tuple[str, str]] = set()

    result = await db.execute(
        select(SkillDocument.skill_id, SkillDocument.document_id)
        .where(SkillDocument.document_id.in_(doc_ids))
    )
    pairs.update((skill_id, doc_id) for skill_id, doc_id in result.all())

    result = await db.execute(
        select(SkillStep.skill_id, StepSource.document_id)
        .join(SkillStep, SkillStep.id == StepSource.step_id)
        .where(StepSource.document_id.in_(doc_ids))
        .distinct()
    )
    pairs.update((skill_id, doc_id) for skill_id, doc_id in result.all())

    if not pairs:
        return None

    max_rel: dict[str, float] = {}
    sum_rel: dict[str, float] = {}
    for skill_id, doc_id in pairs:
        rel = doc_relevance.get(doc_id, 0.0)
        max_rel[skill_id] = max(max_rel.get(skill_id, 0.0), rel)
        sum_rel[skill_id] = sum_rel.get(skill_id, 0.0) + rel

    result = await db.execute(
        select(Skill)
        .options(selectinload(Skill.steps).selectinload(SkillStep.sources))
        .where(Skill.id.in_(max_rel.keys()))
    )
    skills = result.scalars().all()
    if not skills:
        return None

    skill_embeddings = _embedding_service.generate_embeddings(
        [f"{s.name}. {s.description or ''}" for s in skills]
    )
    sim = {
        s.id: _cosine(query_embedding, emb)
        for s, emb in zip(skills, skill_embeddings)
    }

    return max(
        skills,
        key=lambda s: (
            0.5 * sim.get(s.id, 0.0) + 0.5 * max_rel.get(s.id, 0.0),
            sum_rel.get(s.id, 0.0),
            s.confidence,
        ),
    )
