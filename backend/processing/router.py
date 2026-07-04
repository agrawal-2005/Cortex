"""FastAPI router for document processing endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.knowledge.models import Document, Skill, SkillStep
from backend.processing.clustering import TopicClusterer
from backend.processing.lazy_extraction import (
    ExtractionInProgressError,
    LazyExtractionService,
)
from backend.processing.skill_extractor import SkillExtractionPipeline
from backend.processing.renderer import (
    render_skill_dict,
    render_skill_markdown,
)

router = APIRouter(tags=["processing"])


# ── Clustering ────────────────────────────────────────────────────────────


@router.post("/cluster")
async def cluster_documents(
    limit: int = Query(100, ge=1, le=500),
    min_cluster_size: int = Query(3, ge=2, le=50),
    min_samples: int = Query(1, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cluster all documents by semantic similarity."""
    result = await db.execute(
        select(Document).limit(limit).order_by(Document.ingested_at.desc())
    )
    docs = result.scalars().all()

    if not docs:
        return {"clusters": [], "total_documents": 0, "total_clusters": 0}

    doc_dicts = [
        {"id": d.id, "content": d.content}
        for d in docs
    ]

    clusterer = TopicClusterer(
        min_cluster_size=min_cluster_size, min_samples=min_samples
    )
    clusters = clusterer.cluster_documents(doc_dicts)

    return {
        "clusters": clusters,
        "total_documents": len(docs),
        "total_clusters": len(clusters),
    }


# ── Skill extraction ─────────────────────────────────────────────────────


@router.post("/extract")
async def extract_skill_from_cluster(
    document_ids: list[str],
    topic_label: str = Query("general"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Extract a structured skill from a set of documents.

    Provide the document IDs of a topic cluster and a label.
    Returns the extracted skill with confidence scores per step.
    """
    if not document_ids:
        raise HTTPException(status_code=400, detail="document_ids must not be empty")

    pipeline = SkillExtractionPipeline()
    skill = await pipeline.extract_from_cluster(
        db=db,
        document_ids=document_ids,
        topic_label=topic_label,
    )

    await db.commit()

    # Reload with relationships for rendering
    result = await db.execute(
        select(Skill)
        .options(selectinload(Skill.steps).selectinload(SkillStep.sources))
        .where(Skill.id == skill.id)
    )
    skill = result.scalar_one()

    return render_skill_dict(skill)


@router.post("/lazy-extract")
async def lazy_extract(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Cluster all documents and pre-extract only the top clusters.

    Runs automatically after every ingestion — this endpoint exists as a
    manual trigger (e.g. after ingesting data another way or a failed
    run). Everything else is stored as pending topics extracted on demand
    at query time. Full extraction of every cluster is available only via
    the admin script ``scripts/extract_all.py``.
    """
    try:
        return await LazyExtractionService().cluster_and_pre_extract(db)
    except ExtractionInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ── Rendering ─────────────────────────────────────────────────────────────


@router.get("/skills/{skill_id}/render")
async def render_skill(
    skill_id: str,
    format: str = Query("markdown", pattern="^(markdown|plain|json)$"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Render a skill in human-readable format.

    Supported formats: markdown, plain, json.
    """
    result = await db.execute(
        select(Skill)
        .options(
            selectinload(Skill.steps).selectinload(SkillStep.sources)
        )
        .where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    if format == "markdown":
        return {"format": "markdown", "content": render_skill_markdown(skill)}
    elif format == "plain":
        return {"format": "plain", "content": render_skill_markdown(skill)}
    else:
        return render_skill_dict(skill)
