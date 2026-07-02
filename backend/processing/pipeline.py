"""Processing pipeline that orchestrates document-to-skill extraction."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models import Document, Skill, SkillStep
from backend.processing.extractor import SkillExtractor
from backend.processing.embeddings import EmbeddingService
from backend.vectorstore.store import VectorStore
from backend.knowledge.confidence import ConfidenceScorer

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """Orchestrates the full extraction pipeline:
    documents -> skill extraction -> embeddings -> vector store + DB.
    """

    def __init__(self) -> None:
        self.extractor = SkillExtractor()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.confidence_scorer = ConfidenceScorer()

    async def process_documents(self, document_ids: list[str]) -> list[str]:
        """Process documents end-to-end: extract skills, embed, store.

        Args:
            document_ids: List of document IDs to process.

        Returns:
            List of created skill IDs.
        """
        created_skill_ids: list[str] = []

        async with AsyncSessionLocal() as db:
            # Load documents from DB
            documents = await self._load_documents(db, document_ids)
            if not documents:
                logger.warning("No documents found for IDs: %s", document_ids)
                return []

            # Convert ORM objects to dicts for the extractor
            doc_dicts = [
                {
                    "content": doc.content if hasattr(doc, "content") else "",
                    "source_type": doc.source_type if hasattr(doc, "source_type") else "unknown",
                    "source_id": str(doc.id) if hasattr(doc, "id") else "",
                }
                for doc in documents
            ]

            # Extract skills — continue on partial failures
            try:
                extracted_skills = await self.extractor.extract_skills(doc_dicts)
            except Exception as exc:
                logger.error("Skill extraction failed: %s", exc)
                return []

            # Process each extracted skill
            for skill_create in extracted_skills:
                try:
                    skill_id = await self._save_skill(db, skill_create, doc_dicts)
                    created_skill_ids.append(skill_id)
                except Exception as exc:
                    logger.error(
                        "Failed to save skill '%s': %s",
                        skill_create.name,
                        exc,
                    )
                    continue

            await db.commit()

        logger.info(
            "Pipeline complete: processed %d documents, created %d skills",
            len(documents),
            len(created_skill_ids),
        )
        return created_skill_ids

    async def _load_documents(
        self, db: AsyncSession, document_ids: list[str]
    ) -> list[Any]:
        """Load documents from the database by IDs."""
        result = await db.execute(
            select(Document).where(Document.id.in_(document_ids))
        )
        return list(result.scalars().all())

    async def _save_skill(
        self,
        db: AsyncSession,
        skill_create: Any,
        doc_dicts: list[dict[str, Any]],
    ) -> str:
        """Save an extracted skill to DB and vector store.

        Returns:
            The created skill's ID.
        """
        skill_id = str(uuid.uuid4())

        # Calculate confidence score
        # Merge skill_data with steps/description for the scorer
        scorer_data = {
            "steps": [s.model_dump() for s in skill_create.steps],
            "conditions": skill_create.skill_data.get("conditions", []),
            "edge_cases": skill_create.skill_data.get("edge_cases", []),
            "description": skill_create.description,
        }
        source_ids = skill_create.skill_data.get("source_document_ids", [])
        confidence = self.confidence_scorer.calculate_confidence(
            skill_data=scorer_data,
            source_count=len(source_ids),
        )

        # Create Skill ORM object
        skill = Skill(
            id=skill_id,
            name=skill_create.name,
            description=skill_create.description,
            department=skill_create.department,
            status="draft",
            confidence=confidence,
            skill_data=skill_create.skill_data,
        )
        db.add(skill)

        # Create SkillStep ORM objects
        for step_create in skill_create.steps:
            step = SkillStep(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                step_order=step_create.step_order,
                action=step_create.action,
                details=step_create.details,
                confidence=step_create.confidence,
                depends_on=step_create.depends_on,
            )
            db.add(step)

        # Generate embedding from name + description
        embedding_text = f"{skill_create.name}. {skill_create.description}"
        embedding = self.embedding_service.generate_embedding(embedding_text)

        # Store in vector store
        metadata = {
            "name": skill_create.name,
            "status": "draft",
            "confidence": confidence,
        }
        self.vector_store.add_skill(
            skill_id=skill_id,
            text=embedding_text,
            embedding=embedding,
            metadata=metadata,
        )

        return skill_id
