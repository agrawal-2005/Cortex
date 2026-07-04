"""Run the full extraction pipeline on the AcmeTech synthetic documents.

Phase 1 (default): cluster slack/jira/confluence docs and print the clusters.
Phase 2 (--extract): run SkillExtractionPipeline on every cluster.

Usage:
    .venv/bin/python scripts/acmetech_pipeline.py            # cluster only
    .venv/bin/python scripts/acmetech_pipeline.py --extract  # cluster + extract
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.knowledge.models import Document
from backend.processing.clustering import TopicClusterer
from backend.processing.skill_extractor import SkillExtractionPipeline

DB_URL = "postgresql+asyncpg://cortex:cortex@localhost:5432/cortex"
SOURCES = ("slack", "jira", "confluence")
CLUSTERS_FILE = "/tmp/acmetech_clusters.json"


async def main() -> None:
    do_extract = "--extract" in sys.argv
    engine = create_async_engine(DB_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        docs = (
            (
                await db.execute(
                    select(Document).where(Document.source_type.in_(SOURCES))
                )
            )
            .scalars()
            .all()
        )
        print(f"AcmeTech documents: {len(docs)} "
              f"({ {t: sum(1 for d in docs if d.source_type == t) for t in SOURCES} })")

        if os.path.exists(CLUSTERS_FILE) and do_extract:
            clusters = json.load(open(CLUSTERS_FILE))
            print(f"Loaded {len(clusters)} clusters from {CLUSTERS_FILE}")
        else:
            clusterer = TopicClusterer()
            clusters = clusterer.cluster_documents(
                [{"id": d.id, "content": d.content} for d in docs]
            )
            json.dump(clusters, open(CLUSTERS_FILE, "w"))

        by_id = {d.id: d for d in docs}
        for c in sorted(clusters, key=lambda c: -c["document_count"]):
            srcs = {}
            for did in c["document_ids"]:
                st = by_id[did].source_type
                srcs[st] = srcs.get(st, 0) + 1
            print(f"  cluster {c['cluster_id']:>3} ({c['document_count']:>3} docs, {srcs}): {c['topic']}")

        if not do_extract:
            return

        real = [c for c in clusters if c["cluster_id"] != -1]
        print(f"\nExtracting from {len(real)} clusters ...", flush=True)
        pipeline = SkillExtractionPipeline()
        skills = await pipeline.extract_all_clusters(db=db, clusters=clusters)
        print(f"\nExtraction produced {len(skills)} skill rows:")
        for s in skills:
            print(f"  [{s.status:>26}] conf={s.confidence:.2f} "
                  f"repeatable={s.is_repeatable} "
                  f"level={(s.automation_readiness or {}).get('level')} — {s.name}")

    await engine.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main())
