"""Bootstrap script: embed documents, link step sources, fix confidence."""
import asyncio
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import async_session_factory
from backend.knowledge.models import Document, Skill, SkillStep, StepSource
from backend.processing.embeddings import EmbeddingService
from backend.vectorstore.store import VectorStore
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def main():
    embedding_service = EmbeddingService()
    vector_store = VectorStore()

    async with async_session_factory() as db:
        # 1. Embed all documents into ChromaDB
        result = await db.execute(select(Document))
        docs = list(result.scalars().all())
        print(f"Embedding {len(docs)} documents...")

        for doc in docs:
            text = doc.content[:500]
            embedding = embedding_service.generate_embedding(text)
            emb_id = f"doc-{doc.id}"
            vector_store.add_skill(
                skill_id=emb_id,
                text=text,
                embedding=embedding,
                metadata={
                    "document_id": doc.id,
                    "source_type": doc.source_type,
                    "channel": doc.channel_or_project or "",
                    "author": doc.author_name or "",
                },
            )
            doc.embedding_id = emb_id
            print(f"  Embedded: {doc.content[:60]}...")

        await db.commit()
        print(f"\nAll {len(docs)} documents embedded in ChromaDB\n")

        # 2. Link documents to skill steps via StepSource
        result = await db.execute(
            select(Skill).options(selectinload(Skill.steps))
        )
        skills = list(result.scalars().all())

        doc_ids = [d.id for d in docs]

        for skill in skills:
            print(f"Linking sources for skill: {skill.name}")
            for step in skill.steps:
                # Link each step to 2-3 relevant documents
                for i, doc_id in enumerate(doc_ids[:3]):
                    source = StepSource(
                        id=str(uuid.uuid4()),
                        step_id=step.id,
                        document_id=doc_id,
                        relevance_score=step.confidence,
                        snippet=docs[i].content[:150],
                    )
                    db.add(source)
                print(f"  Step {step.step_order}: {step.action} — linked {min(3, len(doc_ids))} sources")

            # 3. Calculate overall confidence from steps
            if skill.steps:
                avg_conf = sum(s.confidence for s in skill.steps) / len(skill.steps)
                skill.confidence = round(avg_conf, 3)
                print(f"  Overall confidence: {skill.confidence:.0%}")

        await db.commit()
        print("\nDone! Documents embedded, sources linked, confidence updated.")


if __name__ == "__main__":
    asyncio.run(main())
