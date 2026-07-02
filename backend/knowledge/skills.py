"""Async CRUD operations for skills."""

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import Skill, SkillStep
from backend.schemas import SkillCreate, SkillUpdate


async def get_skills(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
) -> Sequence[Skill]:
    """List skills with optional pagination and status filter.

    Args:
        db: Async database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        status: Optional status filter (e.g., "draft", "verified").

    Returns:
        List of Skill ORM objects with steps eagerly loaded.
    """
    query = select(Skill).options(selectinload(Skill.steps))
    if status is not None:
        query = query.where(Skill.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_skill(db: AsyncSession, skill_id: str) -> Skill | None:
    """Get a single skill by ID.

    Args:
        db: Async database session.
        skill_id: UUID string of the skill.

    Returns:
        The Skill object (with steps loaded) or None if not found.
    """
    result = await db.execute(
        select(Skill)
        .options(selectinload(Skill.steps))
        .where(Skill.id == skill_id)
    )
    return result.scalar_one_or_none()


async def create_skill(db: AsyncSession, skill: SkillCreate) -> Skill:
    """Create a new skill with its steps in the database.

    Args:
        db: Async database session.
        skill: SkillCreate schema with skill data and optional steps.

    Returns:
        The created Skill ORM object with steps.
    """
    db_skill = Skill(
        id=str(uuid.uuid4()),
        name=skill.name,
        description=skill.description,
        department=skill.department,
        skill_data=skill.skill_data,
        status="draft",
        confidence=0.0,
        version=1,
    )

    # Create associated SkillStep objects
    for step_data in skill.steps:
        step = SkillStep(
            id=str(uuid.uuid4()),
            skill_id=db_skill.id,
            step_order=step_data.step_order,
            action=step_data.action,
            details=step_data.details,
            confidence=step_data.confidence,
            depends_on=step_data.depends_on,
        )
        db_skill.steps.append(step)

    db.add(db_skill)
    await db.commit()
    await db.refresh(db_skill)
    # Re-fetch with eager loading to ensure steps are loaded
    return await get_skill(db, db_skill.id)  # type: ignore[return-value]


async def update_skill(
    db: AsyncSession, skill_id: str, skill_update: SkillUpdate
) -> Skill | None:
    """Update an existing skill.

    Args:
        db: Async database session.
        skill_id: UUID string of the skill to update.
        skill_update: SkillUpdate schema with fields to update.

    Returns:
        The updated Skill object or None if not found.
    """
    skill = await get_skill(db, skill_id)
    if skill is None:
        return None

    update_data = skill_update.model_dump(exclude_unset=True)

    # If verified_by is being set, also stamp verified_at
    if "verified_by" in update_data and update_data["verified_by"] is not None:
        update_data["verified_at"] = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(skill, field, value)

    await db.commit()
    await db.refresh(skill)
    return skill


async def delete_skill(db: AsyncSession, skill_id: str) -> bool:
    """Delete a skill by ID.

    Cascade deletes steps via the relationship configuration.

    Args:
        db: Async database session.
        skill_id: UUID string of the skill to delete.

    Returns:
        True if the skill was deleted, False if not found.
    """
    skill = await get_skill(db, skill_id)
    if skill is None:
        return False

    await db.delete(skill)
    await db.commit()
    return True


async def search_skills(
    db: AsyncSession, query: str
) -> Sequence[Skill]:
    """Search skills by name or description using ILIKE.

    Args:
        db: Async database session.
        query: Search query string.

    Returns:
        List of matching Skill objects with steps loaded.
    """
    search_pattern = f"%{query}%"
    stmt = (
        select(Skill)
        .options(selectinload(Skill.steps))
        .where(
            or_(
                Skill.name.ilike(search_pattern),
                Skill.description.ilike(search_pattern),
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()
