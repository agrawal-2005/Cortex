"""Admin script: extract skills from EVERY topic cluster (no laziness).

The application itself uses lazy extraction — on ingestion only the top
PRE_EXTRACT_TOP_N clusters are extracted and the rest are answered on
demand at query time. This script is the opt-in full run for admins who
want everything extracted up front (e.g. before a demo or an offline
batch job). Expect one LLM call per cluster.

Usage:
    .venv/bin/python scripts/extract_all.py                   # dry run: cluster + list
    .venv/bin/python scripts/extract_all.py --extract         # extract all (bulk model)
    .venv/bin/python scripts/extract_all.py --extract --live  # extract all (GROQ_LIVE_MODEL)
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.config import settings
from backend.knowledge.models import Document
from backend.processing.clustering import TopicClusterer
from backend.processing.skill_extractor import SkillExtractionPipeline


async def main() -> None:
    do_extract = "--extract" in sys.argv
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        docs = (await db.execute(select(Document))).scalars().all()
        print(f"Documents: {len(docs)}")
        if not docs:
            return

        clusters = TopicClusterer().cluster_documents(
            [{"id": d.id, "content": d.content} for d in docs]
        )
        real = [c for c in clusters if c["cluster_id"] != -1]
        for c in sorted(real, key=lambda c: -c["document_count"]):
            print(
                f"  cluster {c['cluster_id']:>3} "
                f"({c['document_count']:>3} docs): {c['topic']}"
            )

        if not do_extract:
            print(f"\n{len(real)} clusters. Re-run with --extract to extract all.")
            return

        groq_model = settings.GROQ_LIVE_MODEL if "--live" in sys.argv else None
        print(
            f"\nExtracting from {len(real)} clusters "
            f"(model: {groq_model or settings.GROQ_MODEL}) ...",
            flush=True,
        )
        pipeline = SkillExtractionPipeline(groq_model=groq_model)
        skills = await pipeline.extract_all_clusters(db=db, clusters=clusters)
        print(f"\nExtraction produced {len(skills)} skill rows:")
        for s in skills:
            print(
                f"  [{s.status:>26}] conf={s.confidence:.2f} "
                f"repeatable={s.is_repeatable} — {s.name}"
            )

    await engine.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main())
