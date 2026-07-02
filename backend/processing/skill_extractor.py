"""Core skill extraction pipeline.

For each topic cluster this module:
1. Retrieves all source documents from PostgreSQL
2. Retrieves past expert feedback for the topic
3. Retrieves source-trust scores
4. Builds a structured extraction prompt (documents + feedback context)
5. Calls the LLM via LangChain / HuggingFace Inference API
6. Parses the JSON response (with resilient error handling)
7. Calculates per-step confidence scores using:
   - source recency, author authority, source-trust, evidence type
8. Persists Skill → SkillSteps → StepSources in PostgreSQL
9. Flags the skill for human review when any step confidence < 0.8
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEndpoint
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.knowledge.models import (
    Document,
    Feedback,
    Skill,
    SkillStep,
    SourceTrust,
    StepSource,
)
from backend.processing.prompts.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
)

logger = logging.getLogger(__name__)

# ── Confidence-scoring constants ──────────────────────────────────────────

# Recency weights (days since document was created)
_RECENCY_BANDS: list[tuple[int, float]] = [
    (30, 0.15),   # < 30 days
    (90, 0.10),   # 30-90 days
    (180, 0.05),  # 90-180 days
]
_RECENCY_DEFAULT = 0.0  # > 180 days or unknown date

# Author-role authority weights (substring match, case-insensitive)
_AUTHORITY_MAP: list[tuple[list[str], float]] = [
    (["director", "vp", "head of", "cto", "ceo", "coo"], 0.15),
    (["lead", "manager", "principal", "staff", "architect"], 0.15),
    (["senior", "sr.", "specialist", "expert"], 0.12),
    (["engineer", "developer", "designer", "analyst", "sre"], 0.08),
    (["coordinator", "associate", "intern", "junior"], 0.04),
]
_AUTHORITY_DEFAULT = 0.02  # unknown role

# Evidence-type weights by source_type
_EVIDENCE_WEIGHTS: dict[str, float] = {
    "jira": 0.10,    # Actual tracked work
    "github": 0.10,  # Code-level evidence
    "notion": 0.07,  # Curated documentation
    "confluence": 0.07,
    "csv": 0.05,
    "json": 0.05,
    "slack": 0.03,   # Informal conversation
}
_EVIDENCE_DEFAULT = 0.02

# Base + max totals
_BASE_CONFIDENCE = 0.40
_MAX_CORROBORATION = 0.05
_REVIEW_THRESHOLD = 0.80


# ── Helpers ───────────────────────────────────────────────────────────────

def _recency_weight(created_at: datetime | None) -> float:
    """Return a recency bonus based on how recent the document is."""
    if created_at is None:
        return _RECENCY_DEFAULT
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    days = (now - created_at).days
    for max_days, weight in _RECENCY_BANDS:
        if days <= max_days:
            return weight
    return _RECENCY_DEFAULT


def _authority_weight(author_role: str | None) -> float:
    """Return an authority bonus based on the author's role."""
    if not author_role:
        return _AUTHORITY_DEFAULT
    role_lower = author_role.lower()
    for keywords, weight in _AUTHORITY_MAP:
        if any(kw in role_lower for kw in keywords):
            return weight
    return _AUTHORITY_DEFAULT


def _evidence_weight(source_type: str | None) -> float:
    """Return an evidence-quality bonus based on the source type."""
    if not source_type:
        return _EVIDENCE_DEFAULT
    return _EVIDENCE_WEIGHTS.get(source_type.lower(), _EVIDENCE_DEFAULT)


def _sanitize_json(text: str) -> str:
    """Best-effort cleanup of LLM-produced JSON.

    Handles:
    - markdown code fences
    - trailing commas before } or ]
    - leading/trailing prose
    """
    # Strip markdown fences
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Find the outermost JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("No JSON object found in response", text, 0)
    text = text[start : end + 1]

    # Remove trailing commas (e.g.  ,} or ,])
    text = re.sub(r",\s*([}\]])", r"\1", text)

    return text


# ── Main pipeline ─────────────────────────────────────────────────────────

class SkillExtractionPipeline:
    """Extracts a single Skill from a topic cluster of documents.

    Typical usage::

        pipeline = SkillExtractionPipeline()
        skill = await pipeline.extract_from_cluster(
            db=session,
            document_ids=["id1", "id2", ...],
            topic_label="deployment process",
        )
    """

    def __init__(self) -> None:
        self._llm: HuggingFaceEndpoint | None = None
        self._chain: Any = None

    # ── LLM setup ─────────────────────────────────────────────────────

    def _get_llm(self) -> HuggingFaceEndpoint:
        if self._llm is None:
            self._llm = HuggingFaceEndpoint(
                repo_id=settings.LLM_MODEL,
                huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
                max_new_tokens=3072,
                temperature=0.1,
                repetition_penalty=1.1,
            )
        return self._llm

    def _get_chain(self) -> Any:
        if self._chain is None:
            prompt = ChatPromptTemplate.from_messages([
                ("system", EXTRACTION_SYSTEM_PROMPT),
                ("human", "{user_prompt}"),
            ])
            self._chain = prompt | self._get_llm() | StrOutputParser()
        return self._chain

    # ── Data retrieval ────────────────────────────────────────────────

    async def _fetch_documents(
        self, db: AsyncSession, document_ids: list[str]
    ) -> list[Document]:
        """Load Document rows by ID."""
        result = await db.execute(
            select(Document).where(Document.id.in_(document_ids))
        )
        return list(result.scalars().all())

    async def _fetch_feedback(
        self, db: AsyncSession, topic_label: str
    ) -> list[Feedback]:
        """Load feedback from any skill whose name resembles the topic.

        This lets expert corrections from prior extraction rounds flow
        into re-extractions of the same topic.
        """
        pattern = f"%{topic_label}%"
        result = await db.execute(
            select(Feedback)
            .join(Skill, Feedback.skill_id == Skill.id)
            .where(Skill.name.ilike(pattern))
            .order_by(Feedback.created_at.desc())
            .limit(20)
        )
        return list(result.scalars().all())

    async def _fetch_trust_scores(
        self, db: AsyncSession, documents: list[Document]
    ) -> dict[str, float]:
        """Build a mapping of source_identifier → trust_score.

        The source_identifier is constructed as ``<source_type>::<channel>``.
        """
        identifiers: set[str] = set()
        for doc in documents:
            ident = f"{doc.source_type}::{doc.channel_or_project or doc.source_id}"
            identifiers.add(ident)

        if not identifiers:
            return {}

        result = await db.execute(
            select(SourceTrust).where(
                SourceTrust.source_identifier.in_(list(identifiers))
            )
        )
        return {
            st.source_identifier: st.trust_score
            for st in result.scalars().all()
        }

    # ── LLM call + parsing ────────────────────────────────────────────

    async def _call_llm(
        self,
        topic_label: str,
        doc_dicts: list[dict[str, Any]],
        feedback_dicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Call the LLM with retries and parse the JSON response."""
        user_prompt = build_extraction_prompt(
            topic_label=topic_label,
            documents=doc_dicts,
            feedback_items=feedback_dicts,
        )

        chain = self._get_chain()
        last_exc: Exception | None = None

        for attempt in range(3):
            try:
                raw: str = await chain.ainvoke({"user_prompt": user_prompt})
                cleaned = _sanitize_json(raw)
                parsed: dict[str, Any] = json.loads(cleaned)
                return parsed
            except json.JSONDecodeError as exc:
                last_exc = exc
                logger.warning(
                    "JSON parse error on attempt %d/3: %s", attempt + 1, exc
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LLM call error on attempt %d/3: %s", attempt + 1, exc
                )
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"Skill extraction failed after 3 attempts: {last_exc}"
        )

    # ── Confidence calculation ────────────────────────────────────────

    def _score_step(
        self,
        step_data: dict[str, Any],
        doc_lookup: dict[str, Document],
        trust_scores: dict[str, float],
    ) -> float:
        """Calculate confidence for a single extracted step.

        Scoring breakdown (max 1.0):
        - Base score:          0.40  (LLM was able to extract the step)
        - Source recency:      up to 0.15  (newer documents → higher)
        - Author authority:    up to 0.15  (senior roles → higher)
        - Source trust:        up to 0.15  (trust table scores)
        - Evidence type:       up to 0.10  (jira > docs > chat)
        - Corroboration:       up to 0.05  (multiple sources agree)
        """
        cited_ids: list[str] = step_data.get("source_document_ids", [])
        cited_docs = [doc_lookup[did] for did in cited_ids if did in doc_lookup]

        if not cited_docs:
            return _BASE_CONFIDENCE  # no citations → base only

        # Recency — best among cited documents
        recency = max(_recency_weight(d.created_at) for d in cited_docs)

        # Authority — best among cited documents
        authority = max(_authority_weight(d.author_role) for d in cited_docs)

        # Source trust — average of trust scores for cited sources
        trust_vals: list[float] = []
        for d in cited_docs:
            ident = f"{d.source_type}::{d.channel_or_project or d.source_id}"
            if ident in trust_scores:
                trust_vals.append(trust_scores[ident])
        trust = (sum(trust_vals) / len(trust_vals) * 0.15) if trust_vals else 0.0

        # Evidence type — best among cited documents
        evidence = max(_evidence_weight(d.source_type) for d in cited_docs)

        # Corroboration — bonus for multiple distinct sources
        corroboration = min(
            _MAX_CORROBORATION, (len(cited_docs) - 1) * 0.02
        )

        score = (
            _BASE_CONFIDENCE
            + recency
            + authority
            + trust
            + evidence
            + corroboration
        )
        return min(1.0, round(score, 3))

    # ── Persistence ───────────────────────────────────────────────────

    async def _persist_skill(
        self,
        db: AsyncSession,
        parsed: dict[str, Any],
        doc_lookup: dict[str, Document],
        trust_scores: dict[str, float],
        topic_label: str,
    ) -> Skill:
        """Create Skill, SkillSteps, and StepSources rows in the database."""

        # --- Score each step ---
        raw_steps: list[dict[str, Any]] = parsed.get("steps", [])
        step_confidences: list[float] = []
        for step_data in raw_steps:
            conf = self._score_step(step_data, doc_lookup, trust_scores)
            step_confidences.append(conf)

        # --- Overall skill confidence (weighted avg of step confidences) ---
        overall_confidence = (
            sum(step_confidences) / len(step_confidences)
            if step_confidences
            else 0.0
        )

        # --- Flag for review if any step is below threshold ---
        needs_review = any(c < _REVIEW_THRESHOLD for c in step_confidences)
        status = "review" if needs_review else "draft"

        # --- Build skill_data (the full executable payload) ---
        skill_data = {
            "conditions": parsed.get("conditions", []),
            "edge_cases": parsed.get("edge_cases", []),
            "prerequisites": parsed.get("prerequisites", []),
            "roles_involved": parsed.get("roles_involved", []),
        }

        skill = Skill(
            id=str(uuid.uuid4()),
            name=parsed.get("name", topic_label),
            description=parsed.get("description", ""),
            department=parsed.get("department"),
            status=status,
            confidence=round(overall_confidence, 3),
            version=1,
            skill_data=skill_data,
        )
        db.add(skill)
        await db.flush()

        # --- Create SkillSteps and StepSources ---
        for idx, step_data in enumerate(raw_steps):
            step = SkillStep(
                id=str(uuid.uuid4()),
                skill_id=skill.id,
                step_order=step_data.get("step_order", idx + 1),
                action=step_data.get("action", ""),
                details=step_data.get("details", {}),
                confidence=step_confidences[idx] if idx < len(step_confidences) else 0.0,
                depends_on=[],
            )
            db.add(step)
            await db.flush()

            # Link each cited document as a StepSource
            cited_ids = step_data.get("source_document_ids", [])
            snippets = step_data.get("source_snippets", [])

            for src_idx, doc_id in enumerate(cited_ids):
                if doc_id not in doc_lookup:
                    continue
                snippet = snippets[src_idx] if src_idx < len(snippets) else ""
                source = StepSource(
                    id=str(uuid.uuid4()),
                    step_id=step.id,
                    document_id=doc_id,
                    relevance_score=step.confidence,
                    snippet=snippet,
                )
                db.add(source)

        await db.flush()
        await db.refresh(skill)

        if needs_review:
            low_steps = [
                f"Step {i + 1} ({step_confidences[i]:.0%})"
                for i in range(len(step_confidences))
                if step_confidences[i] < _REVIEW_THRESHOLD
            ]
            logger.warning(
                "Skill '%s' flagged for review — low confidence steps: %s",
                skill.name,
                ", ".join(low_steps),
            )
        else:
            logger.info(
                "Skill '%s' created with confidence %.0f%%",
                skill.name,
                overall_confidence * 100,
            )

        return skill

    # ── Public API ────────────────────────────────────────────────────

    async def extract_from_cluster(
        self,
        db: AsyncSession,
        document_ids: list[str],
        topic_label: str = "general",
    ) -> Skill:
        """Run the full extraction pipeline for one topic cluster.

        Args:
            db: Async database session.
            document_ids: IDs of documents in this cluster.
            topic_label: Human-readable label for the cluster topic.

        Returns:
            The persisted Skill ORM object (with steps loaded).
        """
        logger.info(
            "Extracting skill for topic '%s' from %d documents",
            topic_label,
            len(document_ids),
        )

        # 1. Retrieve documents
        documents = await self._fetch_documents(db, document_ids)
        if not documents:
            raise ValueError(f"No documents found for IDs: {document_ids}")

        doc_lookup: dict[str, Document] = {d.id: d for d in documents}

        # 2. Retrieve past feedback for this topic
        feedback_rows = await self._fetch_feedback(db, topic_label)

        # 3. Retrieve source trust scores
        trust_scores = await self._fetch_trust_scores(db, documents)

        # 4. Build prompt data
        doc_dicts = [
            {
                "id": d.id,
                "content": d.content,
                "source_type": d.source_type,
                "channel_or_project": d.channel_or_project,
                "author_name": d.author_name,
                "author_role": d.author_role,
                "created_at": d.created_at,
                "source_link": d.source_link,
            }
            for d in documents
        ]
        feedback_dicts = [
            {
                "action": fb.action,
                "original_content": fb.original_content,
                "corrected_content": fb.corrected_content,
                "reason": fb.reason,
                "submitted_by": fb.submitted_by,
            }
            for fb in feedback_rows
        ]

        # 5. Call LLM and parse
        parsed = await self._call_llm(topic_label, doc_dicts, feedback_dicts)

        # 6. Persist with confidence scoring
        skill = await self._persist_skill(
            db, parsed, doc_lookup, trust_scores, topic_label,
        )

        return skill

    async def extract_all_clusters(
        self,
        db: AsyncSession,
        clusters: list[dict[str, Any]],
    ) -> list[Skill]:
        """Extract skills from multiple topic clusters sequentially.

        Args:
            db: Async database session.
            clusters: List of cluster dicts as returned by TopicClusterer,
                      each with ``label``, ``document_ids``, ``cluster_id``.

        Returns:
            List of persisted Skill objects.
        """
        skills: list[Skill] = []

        for cluster in clusters:
            cluster_id = cluster.get("cluster_id", -1)
            if cluster_id == -1:
                logger.info("Skipping noise cluster")
                continue

            label = cluster.get("label", "general")
            doc_ids = cluster.get("document_ids", [])

            # Strip the "doc-" prefix if IDs come from ChromaDB embedding IDs
            clean_ids = [
                did.removeprefix("doc-") if did.startswith("doc-") else did
                for did in doc_ids
            ]

            if not clean_ids:
                continue

            try:
                skill = await self.extract_from_cluster(
                    db=db,
                    document_ids=clean_ids,
                    topic_label=label,
                )
                skills.append(skill)
            except Exception as exc:
                logger.error(
                    "Failed to extract skill for cluster '%s': %s",
                    label,
                    exc,
                )

        logger.info("Extracted %d skills from %d clusters", len(skills), len(clusters))
        return skills
