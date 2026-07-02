from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Feedback
from backend.schemas import FeedbackCreate, FeedbackResponse

router = APIRouter()


class FeedbackUpdate(BaseModel):
    reason: Optional[str] = None
    corrected_content: Optional[str] = None
    submitted_by: Optional[str] = None


@router.post("/", response_model=FeedbackResponse, status_code=201)
async def create_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Create feedback for a skill (and optionally a specific step)."""
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
    return FeedbackResponse.model_validate(feedback)


@router.get("/{skill_id}", response_model=list[FeedbackResponse])
async def get_feedback_for_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[FeedbackResponse]:
    """Get all feedback entries for a given skill."""
    result = await db.execute(
        select(Feedback).where(Feedback.skill_id == skill_id)
    )
    rows = result.scalars().all()
    return [FeedbackResponse.model_validate(r) for r in rows]


@router.patch("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    payload: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Update a feedback entry (e.g., add or change reason, corrected_content)."""
    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feedback, field, value)

    await db.flush()
    await db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)
