"""Data transparency — a full account of what Cortex has ingested.

Powers the /data-overview page: per-source document counts, the date
range covered, sample snippets for verification, and the skills that
were extracted from the data. Read-only; snippets are truncated so the
page shows what KIND of content was pulled in without dumping it all.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.knowledge.models import Document, Skill, SkillDocument

router = APIRouter(tags=["data-overview"])

SNIPPET_LENGTH = 240
SAMPLES_PER_SOURCE = 4


def _snippet(content: str) -> str:
    text = " ".join((content or "").split())
    if len(text) <= SNIPPET_LENGTH:
        return text
    return text[:SNIPPET_LENGTH].rsplit(" ", 1)[0] + "…"


@router.get(
    "/",
    summary="Everything Cortex has ingested",
    description=(
        "Transparency report: document counts and date ranges per source, "
        "truncated sample snippets, and the skills extracted from the data. "
        "Nothing beyond what is listed here has been accessed."
    ),
)
async def data_overview(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    # Effective timestamp: the document's own timestamp when the source
    # provided one, otherwise the moment we ingested it.
    ts = func.coalesce(Document.created_at, Document.ingested_at)

    # ── Per-source counts and date ranges ─────────────────────────────
    rows = (
        await db.execute(
            select(
                Document.source_type,
                func.count(Document.id),
                func.min(ts),
                func.max(ts),
            )
            .group_by(Document.source_type)
            .order_by(func.count(Document.id).desc())
        )
    ).all()

    sources: list[dict[str, Any]] = []
    total_documents = 0
    for source_type, count, earliest, latest in rows:
        total_documents += count

        sample_rows = (
            await db.execute(
                select(Document)
                .where(Document.source_type == source_type)
                .order_by(ts.desc())
                .limit(SAMPLES_PER_SOURCE)
            )
        ).scalars().all()

        sources.append({
            "source_type": source_type,
            "document_count": count,
            "earliest": earliest.isoformat() if earliest else None,
            "latest": latest.isoformat() if latest else None,
            "samples": [
                {
                    "id": d.id,
                    "snippet": _snippet(d.content),
                    "author_name": d.author_name,
                    "channel_or_project": d.channel_or_project,
                    "created_at": (
                        (d.created_at or d.ingested_at).isoformat()
                        if (d.created_at or d.ingested_at) else None
                    ),
                }
                for d in sample_rows
            ],
        })

    # ── Skills extracted from this data ───────────────────────────────
    skill_rows = (
        await db.execute(
            select(Skill)
            .where(Skill.status != "rejected-not-repeatable")
            .order_by(Skill.extracted_at.desc())
        )
    ).scalars().all()

    # Which source types each skill drew from (cluster-level provenance).
    provenance = (
        await db.execute(
            select(SkillDocument.skill_id, Document.source_type)
            .join(Document, Document.id == SkillDocument.document_id)
            .distinct()
        )
    ).all()
    source_types_by_skill: dict[str, list[str]] = {}
    for skill_id, source_type in provenance:
        source_types_by_skill.setdefault(skill_id, []).append(source_type)

    skills = [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status,
            "extracted_at": s.extracted_at.isoformat() if s.extracted_at else None,
            "source_types": sorted(source_types_by_skill.get(s.id, [])),
        }
        for s in skill_rows
    ]

    return {
        "total_documents": total_documents,
        "date_range": {
            "earliest": min(
                (s["earliest"] for s in sources if s["earliest"]), default=None
            ),
            "latest": max(
                (s["latest"] for s in sources if s["latest"]), default=None
            ),
        },
        "sources": sources,
        "skills": skills,
    }
