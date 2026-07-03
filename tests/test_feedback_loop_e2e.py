"""End-to-end feedback loop: extract → reject with correction → re-extract.

Exercises the REAL pipeline (prompt building, JSON parsing, persistence,
feedback retrieval) — only the LLM chain itself is faked. The fake LLM
behaves like a cooperative model: it answers "SLA is 24 hours" unless the
prompt contains an expert correction saying 48 hours, in which case it
obeys the correction. This proves the loop is closed end-to-end:

  1. First extraction has no feedback  → skill says "24 hours".
  2. An expert rejects that step via POST /api/feedback/ with the
     correction "SLA is 48 hours, not 24 hours".
  3. Re-extracting the SAME cluster injects that correction into the
     prompt (EXPERT CORRECTIONS section) → new skill says "48 hours".
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from backend.knowledge.models import Document, SkillStep
from backend.processing.skill_extractor import SkillExtractionPipeline
from tests.conftest import TestSessionLocal

CORRECTION = "SLA is 48 hours, not 24 hours"


def _skill_json(sla_hours: int) -> str:
    """A schema-valid LLM response asserting the given SLA."""
    import json

    return json.dumps(
        {
            "name": "Handle Support Ticket SLA",
            "description": "How support tickets are triaged and answered.",
            "department": "support",
            "roles_involved": ["support engineer"],
            "steps": [
                {
                    "step_order": 1,
                    "action": "Triage the incoming ticket",
                    "details": {"explanation": "Assign severity."},
                    "source_document_ids": [],
                    "source_snippets": [],
                },
                {
                    "step_order": 2,
                    "action": f"Respond within the SLA — SLA is {sla_hours} hours",
                    "details": {"explanation": f"SLA is {sla_hours} hours."},
                    "source_document_ids": [],
                    "source_snippets": [],
                },
                {
                    "step_order": 3,
                    "action": "Close the ticket after confirmation",
                    "details": {"explanation": "Ask the customer to confirm."},
                    "source_document_ids": [],
                    "source_snippets": [],
                },
            ],
            "edge_cases": [],
            "conditions": [],
            "prerequisites": [],
        }
    )


class FakeLLMChain:
    """Stands in for prompt | llm | parser. Records every prompt it
    receives and obeys expert corrections like a real model would."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def ainvoke(self, inputs: dict) -> str:
        user_prompt = inputs["user_prompt"]
        self.prompts.append(user_prompt)
        corrections = user_prompt.split("## EXPERT CORRECTIONS")[-1]
        if "48 hours" in corrections:
            return _skill_json(48)
        return _skill_json(24)


async def _seed_cluster() -> list[str]:
    doc_ids = [str(uuid.uuid4()) for _ in range(3)]
    async with TestSessionLocal() as db:
        for i, did in enumerate(doc_ids):
            db.add(
                Document(
                    id=did,
                    content=f"Ticket thread {i}: customer asked about response SLA.",
                    source_type="slack",
                    source_id=f"src-{did}",
                    channel_or_project="support",
                    author_name="sam",
                )
            )
        await db.commit()
    return doc_ids


@pytest.mark.asyncio
async def test_feedback_loop_end_to_end(client):
    doc_ids = await _seed_cluster()
    fake_chain = FakeLLMChain()
    pipeline = SkillExtractionPipeline()

    # ── 1. First extraction: no feedback exists → skill says 24 hours ──
    with patch.object(pipeline, "_get_chain", return_value=fake_chain):
        async with TestSessionLocal() as db:
            skill_v1 = await pipeline.extract_from_cluster(
                db, doc_ids, topic_label="support sla"
            )
            await db.commit()
            skill_v1_id = skill_v1.id

    assert "(No prior expert corrections for this topic.)" in fake_chain.prompts[0]

    async with TestSessionLocal() as db:
        steps = (
            (
                await db.execute(
                    select(SkillStep).where(SkillStep.skill_id == skill_v1_id)
                )
            )
            .scalars()
            .all()
        )
    sla_step = next(s for s in steps if "SLA" in s.action)
    assert "24 hours" in sla_step.action

    # ── 2. Expert rejects the SLA step through the real API ────────────
    res = await client.post(
        "/api/feedback/",
        json={
            "skill_id": skill_v1_id,
            "step_id": sla_step.id,
            "action": "reject",
            "original_content": sla_step.action,
            "corrected_content": CORRECTION,
            "reason": "The support SLA was changed to 48 hours last quarter.",
            "submitted_by": "expert@example.com",
        },
    )
    assert res.status_code == 201

    # ── 3. Re-extract the same cluster ──────────────────────────────────
    with patch.object(pipeline, "_get_chain", return_value=fake_chain):
        async with TestSessionLocal() as db:
            skill_v2 = await pipeline.extract_from_cluster(
                db, doc_ids, topic_label="support sla"
            )
            await db.commit()
            skill_v2_id = skill_v2.id

    # The correction reached the LLM prompt, inside the corrections section
    reextraction_prompt = fake_chain.prompts[1]
    corrections_section = reextraction_prompt.split("## EXPERT CORRECTIONS")[-1]
    assert CORRECTION in corrections_section
    assert "EXPERT CORRECTION (REJECT)" in corrections_section
    assert "changed to 48 hours last quarter" in corrections_section

    # And the re-extracted skill incorporates it
    async with TestSessionLocal() as db:
        steps_v2 = (
            (
                await db.execute(
                    select(SkillStep).where(SkillStep.skill_id == skill_v2_id)
                )
            )
            .scalars()
            .all()
        )
    sla_step_v2 = next(s for s in steps_v2 if "SLA" in s.action)
    assert "48 hours" in sla_step_v2.action
    assert "24 hours" not in sla_step_v2.action


@pytest.mark.asyncio
async def test_feedback_found_even_when_llm_renames_skill(client):
    """The LLM names the skill something that does NOT contain the cluster
    topic label — feedback must still be found via skill_documents overlap
    (this was the bug: name-ILIKE matching silently dropped feedback)."""
    doc_ids = await _seed_cluster()
    fake_chain = FakeLLMChain()
    pipeline = SkillExtractionPipeline()

    # Skill name "Handle Support Ticket SLA" does not contain this label.
    label = "cluster-7: sla, response, hours"

    with patch.object(pipeline, "_get_chain", return_value=fake_chain):
        async with TestSessionLocal() as db:
            skill_v1 = await pipeline.extract_from_cluster(
                db, doc_ids, topic_label=label
            )
            await db.commit()
            skill_v1_id = skill_v1.id
    assert label.lower() not in skill_v1.name.lower()

    res = await client.post(
        "/api/feedback/",
        json={
            "skill_id": skill_v1_id,
            "action": "reject",
            "corrected_content": CORRECTION,
            "submitted_by": "expert@example.com",
        },
    )
    assert res.status_code == 201

    with patch.object(pipeline, "_get_chain", return_value=fake_chain):
        async with TestSessionLocal() as db:
            skill_v2 = await pipeline.extract_from_cluster(
                db, doc_ids, topic_label=label
            )
            await db.commit()

    assert CORRECTION in fake_chain.prompts[1]
    async with TestSessionLocal() as db:
        actions = (
            (
                await db.execute(
                    select(SkillStep.action).where(
                        SkillStep.skill_id == skill_v2.id
                    )
                )
            )
            .scalars()
            .all()
        )
    assert any("48 hours" in a for a in actions)
