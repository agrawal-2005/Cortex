"""Dump AcmeTech-extracted skills (full JSON) for the honesty evaluation.

Usage: .venv/bin/python scripts/dump_acmetech_skills.py [skill-id-prefix ...]
Without args: lists all skills extracted from slack/jira/confluence docs.
With prefixes: dumps those skills in full.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.knowledge.models import Document, Skill, SkillDocument, SkillStep

DB_URL = "postgresql+asyncpg://cortex:cortex@localhost:5432/cortex"
SOURCES = ("slack", "jira", "confluence")


def full_dump(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "department": skill.department,
        "status": skill.status,
        "confidence": round(skill.confidence, 3),
        "is_repeatable": skill.is_repeatable,
        "trigger": skill.trigger,
        "inputs_schema": skill.inputs_schema,
        "automation_readiness": skill.automation_readiness,
        "skill_data": {
            k: v
            for k, v in (skill.skill_data or {}).items()
            if k in ("prerequisites", "conditions", "edge_cases", "roles_involved")
        },
        "steps": [
            {
                "step_order": s.step_order,
                "action": s.action,
                "confidence": round(s.confidence, 3),
                "details": s.details,
                "sources": [
                    {"document_id": src.document_id[:8], "snippet": src.snippet[:120]}
                    for src in s.sources
                ],
            }
            for s in sorted(skill.steps, key=lambda s: s.step_order)
        ],
    }


async def main() -> None:
    prefixes = [a for a in sys.argv[1:]]
    engine = create_async_engine(DB_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        acme_skill_ids = (
            (
                await db.execute(
                    select(SkillDocument.skill_id)
                    .join(Document, Document.id == SkillDocument.document_id)
                    .where(Document.source_type.in_(SOURCES))
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
        query = (
            select(Skill)
            .options(selectinload(Skill.steps).selectinload(SkillStep.sources))
            .where(Skill.id.in_(acme_skill_ids))
            .order_by(Skill.confidence.desc())
        )
        skills = (await db.execute(query)).scalars().all()

        if not prefixes:
            for s in skills:
                ar = (s.automation_readiness or {}).get("level")
                print(
                    f"{s.id[:8]}  conf={s.confidence:.2f} steps={len(s.steps)} "
                    f"inputs={len(s.inputs_schema or {})} level={ar} "
                    f"[{s.status}] {s.name}"
                )
        else:
            for s in skills:
                if any(s.id.startswith(p) for p in prefixes):
                    print(json.dumps(full_dump(s), indent=2))
                    print("\n" + "=" * 72 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
