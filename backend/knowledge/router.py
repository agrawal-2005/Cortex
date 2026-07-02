"""FastAPI router for skill endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import SkillCreate, SkillResponse, SkillUpdate
from backend.knowledge import skills as skill_crud

router = APIRouter(tags=["skills"])


@router.get("/", response_model=list[SkillResponse])
async def list_skills(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> list:
    """List skills with pagination and optional status filter."""
    results = await skill_crud.get_skills(db, skip=skip, limit=limit, status=status)
    return list(results)


@router.get("/search", response_model=list[SkillResponse])
async def search_skills(
    query: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_db),
) -> list:
    """Search skills by name or description."""
    results = await skill_crud.search_skills(db, query)
    return list(results)


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> SkillResponse:
    """Get a single skill by ID."""
    skill = await skill_crud.get_skill(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.post("/", response_model=SkillResponse, status_code=201)
async def create_skill(
    skill_create: SkillCreate,
    db: AsyncSession = Depends(get_db),
) -> SkillResponse:
    """Create a new skill with optional steps."""
    skill = await skill_crud.create_skill(db, skill_create)
    return skill


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    skill_update: SkillUpdate,
    db: AsyncSession = Depends(get_db),
) -> SkillResponse:
    """Update an existing skill."""
    skill = await skill_crud.update_skill(db, skill_id, skill_update)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a skill by ID."""
    deleted = await skill_crud.delete_skill(db, skill_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/{skill_id}/execute")
async def execute_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Execute a skill -- returns the skill's steps as an execution plan.

    This is a placeholder that returns a structured execution plan
    based on the skill's defined steps.
    """
    skill = await skill_crud.get_skill(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    steps = skill.steps or []

    return {
        "skill_id": skill.id,
        "name": skill.name,
        "status": "execution_plan",
        "steps": [
            {
                "step_id": step.id,
                "order": step.step_order,
                "action": step.action,
                "details": step.details,
                "confidence": step.confidence,
                "depends_on": step.depends_on,
                "status": "pending",
            }
            for step in steps
        ],
        "total_steps": len(steps),
    }
