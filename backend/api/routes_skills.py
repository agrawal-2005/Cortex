"""Skills API routes — list, detail, executable format."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.knowledge.models import Skill, SkillStep
from backend.processing.renderer import render_skill_dict, render_skill_markdown
from backend.schemas import SkillResponse

router = APIRouter(tags=["skills"])


# ── GET / — List skills with filters ──────────────────────────────────────


@router.get(
    "/",
    summary="List all skills",
    description=(
        "Paginated list of skills. Filter by status, department, and "
        "minimum confidence. Results include step counts."
    ),
)
async def list_skills(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    status: str | None = Query(None, description="Filter: draft, review, verified, outdated"),
    department: str | None = Query(None, description="Filter by department"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    search: str | None = Query(None, description="Search in name/description"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(Skill).options(selectinload(Skill.steps))

    if status:
        query = query.where(Skill.status == status)
    if department:
        query = query.where(Skill.department == department)
    if min_confidence is not None:
        query = query.where(Skill.confidence >= min_confidence)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            Skill.name.ilike(pattern) | Skill.description.ilike(pattern)
        )

    # Total count (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginated results
    query = query.order_by(Skill.extracted_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    skills = result.scalars().unique().all()

    items = []
    for skill in skills:
        items.append({
            "id": skill.id,
            "name": skill.name,
            "description": skill.description[:200],
            "department": skill.department,
            "status": skill.status,
            "confidence": skill.confidence,
            "version": skill.version,
            "step_count": len(skill.steps),
            "needs_review": any(
                s.confidence < 0.8 for s in skill.steps
            ),
            "extracted_at": skill.extracted_at.isoformat() if skill.extracted_at else None,
            "verified_by": skill.verified_by,
        })

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


# ── GET /{id} — Full skill with human-readable version ────────────────────


@router.get(
    "/{skill_id}",
    summary="Get full skill detail",
    description=(
        "Returns the complete skill with steps, source citations, "
        "confidence scores, and a human-readable markdown rendering."
    ),
)
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Skill)
        .options(
            selectinload(Skill.steps).selectinload(SkillStep.sources),
            selectinload(Skill.feedback),
        )
        .where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    rendered = render_skill_dict(skill)
    rendered["markdown"] = render_skill_markdown(skill)

    return rendered


# ── GET /{id}/executable — Machine-readable for AI agents ────────────────


@router.get(
    "/{skill_id}/executable",
    summary="Get executable skill for AI agents",
    description=(
        "Returns a machine-readable version optimized for execution "
        "by AI agents. Includes ordered steps with tools, conditions, "
        "expected outputs, and dependency graph."
    ),
)
async def get_executable_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Skill)
        .options(selectinload(Skill.steps))
        .where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill_data: dict[str, Any] = skill.skill_data or {}
    steps = sorted(skill.steps, key=lambda s: s.step_order)

    return {
        "schema_version": "1.0",
        "skill_id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "department": skill.department,
        "confidence": skill.confidence,
        "prerequisites": skill_data.get("prerequisites", []),
        "conditions": skill_data.get("conditions", []),
        "roles_required": skill_data.get("roles_involved", []),
        "execution_plan": [
            {
                "step_id": step.id,
                "order": step.step_order,
                "action": step.action,
                "explanation": step.details.get("explanation", ""),
                "tools": step.details.get("tools", []),
                "conditions": step.details.get("conditions"),
                "expected_output": step.details.get("expected_output"),
                "confidence": step.confidence,
                "depends_on": step.depends_on,
                "status": "pending",
            }
            for step in steps
        ],
        "edge_cases": skill_data.get("edge_cases", []),
        "total_steps": len(steps),
        "estimated_confidence": skill.confidence,
    }
