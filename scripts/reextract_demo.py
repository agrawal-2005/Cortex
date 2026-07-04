"""Re-extraction demo: run the new automation-ready extraction prompt on the
document clusters of a few existing skills and print before/after.

Usage: .venv/bin/python scripts/reextract_demo.py
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.knowledge.models import Skill, SkillStep, SkillDocument
from backend.processing.skill_extractor import SkillExtractionPipeline

DB_URL = "postgresql+asyncpg://cortex:cortex@localhost:5432/cortex"

# (old_skill_id, topic_label)
TARGETS = [
    ("1c0c32e0", "ignore dependabot version"),
    ("dfb53a0b", "apply dependabot fix"),
    ("e9e0af61", "phase 1 identity differential implementation"),
]


def dump_skill(skill: Skill, title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")
    print(f"name:        {skill.name}")
    print(f"status:      {skill.status}")
    print(f"confidence:  {skill.confidence:.2f}")
    print(f"repeatable:  {skill.is_repeatable}")
    print(f"trigger:     {json.dumps(skill.trigger) if skill.trigger else None}")
    print(f"inputs_schema: {json.dumps(skill.inputs_schema or {}, indent=2)}")
    print(f"automation_readiness: {json.dumps(skill.automation_readiness or {}, indent=2)}")
    steps = sorted(skill.steps, key=lambda s: s.step_order)
    print(f"steps ({len(steps)}):")
    for s in steps:
        d = s.details or {}
        print(f"  {s.step_order}. [{s.confidence:.2f}] {s.action}")
        tool = d.get("tool")
        if tool:
            print(f"       tool: {json.dumps(tool)}")
        if d.get("command"):
            print(f"       command: {d['command']}")
        if d.get("success_criteria"):
            print(f"       success: {d['success_criteria']}")
        if d.get("inputs_required"):
            print(f"       inputs_required: {d['inputs_required']}")
        if not tool and not d.get("command"):
            expl = (d.get("explanation") or "")[:110]
            print(f"       explanation: {expl}")


async def main() -> None:
    engine = create_async_engine(DB_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    pipeline = SkillExtractionPipeline()

    async with Session() as db:
        for prefix, topic in TARGETS:
            old = (
                await db.execute(
                    select(Skill)
                    .options(selectinload(Skill.steps).selectinload(SkillStep.sources))
                    .where(Skill.id.like(f"{prefix}%"))
                )
            ).scalar_one()

            doc_ids = [
                r
                for r in (
                    await db.execute(
                        select(SkillDocument.document_id).where(
                            SkillDocument.skill_id == old.id
                        )
                    )
                ).scalars()
            ]
            dump_skill(old, f"BEFORE — {old.name} ({old.id[:8]}, {len(doc_ids)} cluster docs)")

            print(f"\n--- re-extracting '{topic}' from {len(doc_ids)} docs ---", flush=True)
            try:
                new = await pipeline.extract_from_cluster(
                    db=db, document_ids=doc_ids, topic_label=topic
                )
            except Exception as exc:  # noqa: BLE001
                print(f"EXTRACTION FAILED: {type(exc).__name__}: {exc}")
                await db.rollback()
                continue
            await db.commit()

            new = (
                await db.execute(
                    select(Skill)
                    .options(selectinload(Skill.steps).selectinload(SkillStep.sources))
                    .where(Skill.id == new.id)
                )
            ).scalar_one()
            dump_skill(new, f"AFTER — {new.name} ({new.id[:8]})")
            if new.status == "rejected-not-repeatable":
                print(f"  >> rejection reason: {(new.skill_data or {}).get('rejection_reason')}")

    await engine.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main())
