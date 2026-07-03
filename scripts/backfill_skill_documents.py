"""Backfill skill_documents for skills extracted before the table existed.

Legacy skills only have step_sources (the handful of documents the LLM
cited). This script reconstructs cluster-level provenance:

1. Cluster all documents with the live TopicClusterer.
2. For each cluster, find the skill with the most step_source citations
   among the cluster's members — that skill was extracted from this
   cluster (or its closest ancestor).
3. Link EVERY document in the cluster to that skill via skill_documents.

Idempotent: existing (skill_id, document_id) pairs are skipped.

Run from the repo root:

    .venv/bin/python scripts/backfill_skill_documents.py
"""

import asyncio
from collections import Counter

from sqlalchemy import select

from backend.database import async_session_factory
from backend.knowledge.models import (
    Document,
    Skill,
    SkillDocument,
    SkillStep,
    StepSource,
)
from backend.processing.clustering import TopicClusterer


async def main() -> None:
    async with async_session_factory() as db:
        # ── Load documents ─────────────────────────────────────────────
        docs = (await db.execute(select(Document))).scalars().all()
        print(f"Documents: {len(docs)}")

        # ── Map document_id -> citing skill_ids (via step_sources) ─────
        rows = (
            await db.execute(
                select(StepSource.document_id, SkillStep.skill_id)
                .join(SkillStep, StepSource.step_id == SkillStep.id)
            )
        ).all()
        doc_to_skills: dict[str, set[str]] = {}
        for doc_id, skill_id in rows:
            doc_to_skills.setdefault(doc_id, set()).add(skill_id)
        print(f"Documents cited in step_sources: {len(doc_to_skills)}")

        skills = (await db.execute(select(Skill))).scalars().all()
        skill_names = {s.id: s.name for s in skills}
        print(f"Skills: {len(skills)}")

        # ── Existing links (idempotency) ───────────────────────────────
        existing = {
            (r[0], r[1])
            for r in (
                await db.execute(
                    select(SkillDocument.skill_id, SkillDocument.document_id)
                )
            ).all()
        }
        print(f"Existing skill_documents links: {len(existing)}")

        # ── Cluster all documents ──────────────────────────────────────
        clusterer = TopicClusterer()
        clusters = clusterer.cluster_documents(
            [{"id": d.id, "content": d.content} for d in docs]
        )
        real = [c for c in clusters if c["cluster_id"] != -1]
        print(f"Clusters: {len(real)} (plus noise)")

        # ── Match clusters to skills and link members ──────────────────
        added = 0
        matched_clusters = 0
        for cluster in real:
            member_ids = [
                did.removeprefix("doc-") for did in cluster["document_ids"]
            ]

            # Count citations per skill among this cluster's members
            votes: Counter[str] = Counter()
            for did in member_ids:
                for skill_id in doc_to_skills.get(did, ()):
                    votes[skill_id] += 1

            if not votes:
                continue

            skill_id, n_votes = votes.most_common(1)[0]
            matched_clusters += 1
            print(
                f"  cluster {cluster['cluster_id']:>3} "
                f"({len(member_ids)} docs, topic '{cluster['topic']}') "
                f"-> '{skill_names.get(skill_id, skill_id)}' "
                f"({n_votes} citation(s))"
            )

            for did in member_ids:
                if (skill_id, did) in existing:
                    continue
                db.add(SkillDocument(skill_id=skill_id, document_id=did))
                existing.add((skill_id, did))
                added += 1

        await db.commit()
        print(
            f"\nDone: {matched_clusters}/{len(real)} clusters matched to a "
            f"skill, {added} skill_documents rows added."
        )


if __name__ == "__main__":
    asyncio.run(main())
