"""Feedback API routes — submit feedback with auto trust-score updates."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.knowledge.models import (
    Document,
    Feedback,
    Skill,
    SkillStep,
    SourceTrust,
    StepSource,
)
from backend.schemas import FeedbackCreate, FeedbackResponse

router = APIRouter(tags=["feedback"])


# ── POST / — Submit feedback ─────────────────────────────────────────────


@router.post(
    "/",
    response_model=FeedbackResponse,
    status_code=201,
    summary="Submit feedback on a skill or step",
    description=(
        "Submit an approve, edit, or reject action. "
        "Source trust scores are automatically updated based on the "
        "feedback action and the documents cited by the affected step."
    ),
)
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    # Validate skill exists
    skill = (
        await db.execute(select(Skill).where(Skill.id == payload.skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Validate step if provided
    if payload.step_id:
        step = (
            await db.execute(
                select(SkillStep).where(SkillStep.id == payload.step_id)
            )
        ).scalar_one_or_none()
        if step is None:
            raise HTTPException(status_code=404, detail="Step not found")

    # Create feedback record
    feedback = Feedback(
        skill_id=payload.skill_id,
        step_id=payload.step_id,
        action=payload.action,
        original_content=payload.original_content,
        corrected_content=payload.corrected_content,
        reason=payload.reason,
        submitted_by=payload.submitted_by,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)

    # Update skill status based on feedback action
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.action == "approve":
        skill.status = "verified"
        skill.verified_by = payload.submitted_by
        skill.verified_at = now
    elif payload.action == "reject":
        skill.status = "outdated"
    elif payload.action == "edit":
        skill.status = "review"
        # Atomic server-side increment — a plain `version += 1` is a
        # read-modify-write that loses updates under concurrent feedback.
        skill.version = Skill.version + 1

    await db.flush()

    # Auto-update source trust scores
    await _update_source_trust(db, payload)

    return FeedbackResponse.model_validate(feedback)


# ── GET /history/{skill_id} — Feedback history ───────────────────────────


@router.get(
    "/history/{skill_id}",
    response_model=list[FeedbackResponse],
    summary="Get feedback history for a skill",
)
async def get_feedback_history(
    skill_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[FeedbackResponse]:
    result = await db.execute(
        select(Feedback)
        .where(Feedback.skill_id == skill_id)
        .order_by(Feedback.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = result.scalars().all()
    return [FeedbackResponse.model_validate(r) for r in rows]


# ── Source trust auto-update ──────────────────────────────────────────────


async def _update_source_trust(
    db: AsyncSession,
    payload: FeedbackCreate,
) -> None:
    """Update source_trust scores for documents cited by the affected step.

    - approve  → times_approved += 1, trust_score nudged up
    - edit     → neutral (content was partially right)
    - reject   → times_rejected += 1, trust_score nudged down

    Trust score is recalculated as:
        trust = (approved + 0.5 * cited) / (approved + rejected + cited)
    clamped to [0.1, 1.0].
    """
    # Find which documents are cited by the step (or all skill steps)
    if payload.step_id:
        result = await db.execute(
            select(StepSource).where(StepSource.step_id == payload.step_id)
        )
    else:
        # Get all steps for the skill, then all their sources
        step_result = await db.execute(
            select(SkillStep.id).where(SkillStep.skill_id == payload.skill_id)
        )
        step_ids = [r[0] for r in step_result.all()]
        if not step_ids:
            return
        result = await db.execute(
            select(StepSource).where(StepSource.step_id.in_(step_ids))
        )

    step_sources = result.scalars().all()
    if not step_sources:
        return

    # Get unique document IDs
    doc_ids = list({ss.document_id for ss in step_sources})

    # Load documents to build source identifiers
    doc_result = await db.execute(
        select(Document).where(Document.id.in_(doc_ids))
    )
    documents = doc_result.scalars().all()

    for doc in documents:
        identifier = f"{doc.source_type}::{doc.channel_or_project or doc.source_id}"

        # Upsert source trust record
        trust_result = await db.execute(
            select(SourceTrust).where(
                SourceTrust.source_identifier == identifier
            )
        )
        trust = trust_result.scalar_one_or_none()

        if trust is None:
            trust = SourceTrust(
                source_identifier=identifier,
                times_cited=1,
                times_approved=0,
                times_rejected=0,
                trust_score=0.5,
            )
            db.add(trust)

        # Update counters based on action
        trust.times_cited += 1
        if payload.action == "approve":
            trust.times_approved += 1
        elif payload.action == "reject":
            trust.times_rejected += 1
        # "edit" — neutral, just increment times_cited

        # Recalculate trust score
        total = trust.times_approved + trust.times_rejected + trust.times_cited
        if total > 0:
            raw_score = (trust.times_approved + 0.5 * trust.times_cited) / total
            trust.trust_score = max(0.1, min(1.0, round(raw_score, 3)))

        trust.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.flush()
