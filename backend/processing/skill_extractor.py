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
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.knowledge.models import (
    Document,
    Feedback,
    Skill,
    SkillDocument,
    SkillStep,
    SourceTrust,
    StepSource,
)
from backend.processing.prompts.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
)

logger = logging.getLogger(__name__)

# ── Prompt-size guards ────────────────────────────────────────────────────
# Llama-3.1 has a 128k-token context (~4 chars/token). Large clusters must be
# capped or the provider rejects the request outright.
MAX_PROMPT_DOCS = 40
MAX_DOC_CHARS = 4000

# ── LLM failure-handling constants ───────────────────────────────────────
MAX_LLM_ATTEMPTS = 3
LLM_TIMEOUT_SECONDS = 60.0          # per-call hard limit
RETRY_BACKOFF_BASE = 1.0            # generic retry: 1s, 2s
RATE_LIMIT_BACKOFF_BASE = 5.0       # 429 retry: 5s, 10s
MIN_SKILL_STEPS = 3                 # a skill with fewer steps is rejected

# Appended to the user prompt when a previous attempt returned unusable
# output (bad JSON or wrong schema).
STRICT_FORMAT_REMINDER = (
    "\n\n## STRICT FORMAT REMINDER\n"
    "Your previous response could not be used. You MUST respond with ONLY "
    "one complete, valid JSON object — no prose, no markdown fences, no "
    "truncation. The object MUST contain a \"steps\" array with at least "
    f"{MIN_SKILL_STEPS} step objects, each citing source documents. Do not "
    "include any text before or after the JSON object."
)


class LLMCreditsExhaustedError(RuntimeError):
    """The LLM provider returned HTTP 402 — credits exhausted.

    Non-retryable: extraction must stop gracefully, keeping completed
    skills and reporting the clusters that remain.
    """


class LLMTimeoutError(RuntimeError):
    """The LLM call exceeded LLM_TIMEOUT_SECONDS.

    Non-retryable for the current cluster — the pipeline moves on.
    """


class SchemaValidationError(ValueError):
    """The LLM returned valid JSON that does not match the skill schema."""


class EmptyLLMResponseError(RuntimeError):
    """The LLM returned an empty or whitespace-only response."""


async def _sleep(seconds: float) -> None:
    """Indirection over asyncio.sleep so tests can stub retry delays."""
    await asyncio.sleep(seconds)


_STATUS_CODE_PATTERN = re.compile(r"\b(402|429|500|502|503|504)\b")


def _http_status_of(exc: BaseException) -> int | None:
    """Best-effort extraction of an HTTP status code from a provider error.

    huggingface_hub raises HfHubHTTPError with a ``.response`` attribute;
    other layers may only carry the code (or a recognisable phrase) in the
    message.
    """
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status

    message = str(exc)
    match = _STATUS_CODE_PATTERN.search(message)
    if match:
        return int(match.group(1))

    lowered = message.lower()
    if "payment required" in lowered or "exceeded your monthly included credits" in lowered:
        return 402
    if "rate limit" in lowered or "too many requests" in lowered:
        return 429
    return None


def _validate_skill_schema(parsed: dict[str, Any]) -> None:
    """Reject LLM output that parses as JSON but is not a usable skill."""
    if not isinstance(parsed, dict):
        raise SchemaValidationError("response is not a JSON object")
    steps = parsed.get("steps")
    if steps is None:
        raise SchemaValidationError('missing required "steps" field')
    if not isinstance(steps, list):
        raise SchemaValidationError('"steps" must be an array')
    if len(steps) < MIN_SKILL_STEPS:
        raise SchemaValidationError(
            f"skill has {len(steps)} step(s); at least {MIN_SKILL_STEPS} required"
        )

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


def _repair_json(text: str) -> str:
    """Append the closing braces/brackets a truncated JSON object is missing.

    Walks the text tracking string/escape state, then closes any containers
    that were left open (a common LLM failure: output cut off mid-object).
    """
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()

    if in_string:
        text += '"'
    closers = {"{": "}", "[": "]"}
    return text + "".join(closers[c] for c in reversed(stack))


def _sanitize_json(text: str) -> str:
    """Best-effort cleanup of LLM-produced JSON.

    Handles:
    - markdown code fences
    - trailing commas before } or ]
    - leading/trailing prose
    - truncated output missing closing braces/brackets (repaired)
    """
    # Strip markdown fences
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found in response", text, 0)

    # Happy path: a complete outermost object exists
    end = text.rfind("}")
    if end > start:
        candidate = re.sub(r",\s*([}\]])", r"\1", text[start : end + 1])
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass  # fall through to repair

    # Repair path: assume the JSON runs to the end of the text but was
    # truncated — balance the missing closers.
    candidate = _repair_json(text[start:].rstrip())
    return re.sub(r",\s*([}\]])", r"\1", candidate)


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
            endpoint = HuggingFaceEndpoint(
                repo_id=settings.LLM_MODEL,
                huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
                max_new_tokens=3072,
                temperature=0.1,
                repetition_penalty=1.1,
            )
            # HF Inference Providers only expose chat models via the
            # chat-completions ("conversational") API, so wrap the endpoint.
            self._llm = ChatHuggingFace(llm=endpoint)
        return self._llm

    def _get_chain(self) -> Any:
        if self._chain is None:
            # Both messages are injected as variables: the system prompt
            # contains a literal JSON schema and document content may contain
            # braces — neither must be parsed as template placeholders.
            prompt = ChatPromptTemplate.from_messages([
                ("system", "{system_prompt}"),
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
        self, db: AsyncSession, topic_label: str, document_ids: list[str]
    ) -> list[Feedback]:
        """Load expert feedback from prior extraction rounds of this topic.

        Primary match: feedback on skills previously extracted from a
        cluster sharing documents with this one (skill_documents
        provenance). Cluster topic labels and LLM-chosen skill names
        rarely coincide, so document overlap — not the name — is what
        reliably identifies "the same topic, extracted before".

        Fallback match: skill name resembles the topic label (covers
        legacy skills extracted before skill_documents existed).
        """
        prior_skill_ids = select(SkillDocument.skill_id).where(
            SkillDocument.document_id.in_(document_ids)
        )
        named_skill_ids = select(Skill.id).where(
            Skill.name.ilike(f"%{topic_label}%")
        )
        result = await db.execute(
            select(Feedback)
            .where(
                or_(
                    Feedback.skill_id.in_(prior_skill_ids),
                    Feedback.skill_id.in_(named_skill_ids),
                )
            )
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
        """Call the LLM with retries and parse the JSON response.

        Failure handling:
        - empty response / bad JSON / wrong schema → retry (schema and JSON
          failures retry with a stricter prompt appended)
        - timeout (> LLM_TIMEOUT_SECONDS)          → LLMTimeoutError, no retry
        - HTTP 402 (credits exhausted)             → LLMCreditsExhaustedError,
          no retry — the caller stops extraction gracefully
        - HTTP 429 (rate limit)                    → longer exponential backoff
        - other errors (e.g. HTTP 500)             → standard backoff retry
        """
        base_prompt = build_extraction_prompt(
            topic_label=topic_label,
            documents=doc_dicts,
            feedback_items=feedback_dicts,
        )

        chain = self._get_chain()
        last_exc: Exception | None = None
        user_prompt = base_prompt

        for attempt in range(MAX_LLM_ATTEMPTS):
            try:
                raw: str = await asyncio.wait_for(
                    chain.ainvoke({
                        "system_prompt": EXTRACTION_SYSTEM_PROMPT,
                        "user_prompt": user_prompt,
                    }),
                    timeout=LLM_TIMEOUT_SECONDS,
                )
                if not raw or not raw.strip():
                    raise EmptyLLMResponseError("LLM returned an empty response")
                cleaned = _sanitize_json(raw)
                parsed: dict[str, Any] = json.loads(cleaned)
                _validate_skill_schema(parsed)
                return parsed
            except asyncio.TimeoutError as exc:
                logger.error(
                    "LLM call timed out after %.0fs for topic '%s' — skipping cluster",
                    LLM_TIMEOUT_SECONDS,
                    topic_label,
                )
                raise LLMTimeoutError(
                    f"LLM call for topic '{topic_label}' timed out "
                    f"after {LLM_TIMEOUT_SECONDS:.0f}s"
                ) from exc
            except EmptyLLMResponseError as exc:
                last_exc = exc
                logger.warning(
                    "Empty LLM response on attempt %d/%d for topic '%s'",
                    attempt + 1, MAX_LLM_ATTEMPTS, topic_label,
                )
            except SchemaValidationError as exc:
                last_exc = exc
                logger.warning(
                    "Schema validation failed on attempt %d/%d: %s — "
                    "retrying with stricter prompt",
                    attempt + 1, MAX_LLM_ATTEMPTS, exc,
                )
                user_prompt = base_prompt + STRICT_FORMAT_REMINDER
            except json.JSONDecodeError as exc:
                last_exc = exc
                logger.warning(
                    "JSON parse error on attempt %d/%d: %s",
                    attempt + 1, MAX_LLM_ATTEMPTS, exc,
                )
                user_prompt = base_prompt + STRICT_FORMAT_REMINDER
            except Exception as exc:
                status = _http_status_of(exc)
                if status == 402:
                    logger.error(
                        "LLM credits exhausted (HTTP 402) — stopping extraction: %s",
                        exc,
                    )
                    raise LLMCreditsExhaustedError(str(exc)) from exc
                last_exc = exc
                if status == 429:
                    logger.warning(
                        "Rate limited (HTTP 429) on attempt %d/%d: %s",
                        attempt + 1, MAX_LLM_ATTEMPTS, exc,
                    )
                    if attempt < MAX_LLM_ATTEMPTS - 1:
                        await _sleep(RATE_LIMIT_BACKOFF_BASE * (2 ** attempt))
                    continue
                logger.warning(
                    "LLM call error on attempt %d/%d: %s",
                    attempt + 1, MAX_LLM_ATTEMPTS, exc,
                )
            if attempt < MAX_LLM_ATTEMPTS - 1:
                await _sleep(RETRY_BACKOFF_BASE * (2 ** attempt))

        raise RuntimeError(
            f"Skill extraction failed after {MAX_LLM_ATTEMPTS} attempts: {last_exc}"
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
        # LLMs sometimes emit explicit nulls ("source_document_ids": null);
        # .get() with a default does not cover that, so coalesce with `or`.
        cited_ids: list[str] = step_data.get("source_document_ids") or []
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
        # `or` coalescing throughout: the LLM may emit explicit nulls for
        # any of these fields, which .get() defaults do not cover.
        skill_data = {
            "conditions": parsed.get("conditions") or [],
            "edge_cases": parsed.get("edge_cases") or [],
            "prerequisites": parsed.get("prerequisites") or [],
            "roles_involved": parsed.get("roles_involved") or [],
        }

        skill = Skill(
            id=str(uuid.uuid4()),
            name=parsed.get("name") or topic_label,
            description=parsed.get("description") or "",
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
                action=step_data.get("action") or "",
                details=step_data.get("details") or {},
                confidence=step_confidences[idx] if idx < len(step_confidences) else 0.0,
                depends_on=[],
            )
            db.add(step)
            await db.flush()

            # Link each cited document as a StepSource
            cited_ids = step_data.get("source_document_ids") or []
            snippets = step_data.get("source_snippets") or []

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
        feedback_rows = await self._fetch_feedback(db, topic_label, document_ids)

        # 3. Retrieve source trust scores
        trust_scores = await self._fetch_trust_scores(db, documents)

        # 4. Build prompt data (capped so huge clusters fit the LLM context)
        prompt_docs = documents[:MAX_PROMPT_DOCS]
        if len(documents) > MAX_PROMPT_DOCS:
            logger.warning(
                "Cluster '%s' has %d documents; sending only the first %d to the LLM",
                topic_label, len(documents), MAX_PROMPT_DOCS,
            )
        doc_dicts = [
            {
                "id": d.id,
                "content": d.content[:MAX_DOC_CHARS],
                "source_type": d.source_type,
                "channel_or_project": d.channel_or_project,
                "author_name": d.author_name,
                "author_role": d.author_role,
                "created_at": d.created_at,
                "source_link": d.source_link,
            }
            for d in prompt_docs
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

        # 7. Record cluster-level provenance: EVERY document in the source
        # cluster links to this skill (not just the few cited in
        # step_sources), so the query route can map any relevant document
        # back to the skill extracted from its cluster.
        for doc in documents:
            db.add(SkillDocument(skill_id=skill.id, document_id=doc.id))
        await db.flush()

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
                      each with ``topic``, ``document_ids``, ``cluster_id``.

        Returns:
            List of persisted Skill objects.

        Each successfully extracted skill is committed immediately, so a
        failure in a later cluster never rolls back earlier work.  A 402
        (credits exhausted) stops extraction gracefully and logs which
        clusters remain unprocessed.
        """
        skills: list[Skill] = []
        # session.rollback() (after a failed cluster or a 402) expires ALL
        # instances in the session — including previously committed skills.
        # Attribute access on an expired instance triggers synchronous lazy
        # IO, which raises MissingGreenlet under an async session. Capture
        # IDs eagerly and reload fresh rows before returning.
        skill_ids: list[str] = []

        for index, cluster in enumerate(clusters):
            cluster_id = cluster.get("cluster_id", -1)
            if cluster_id == -1:
                logger.info("Skipping noise cluster")
                continue

            # TopicClusterer emits "topic"; accept "label" for compatibility.
            label = cluster.get("topic") or cluster.get("label", "general")
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
                skill_ids.append(skill.id)
                # Commit per cluster — each skill cost an LLM call and must
                # survive failures in later clusters.
                await db.commit()
            except LLMCreditsExhaustedError:
                await db.rollback()
                remaining = [
                    c.get("topic") or c.get("label", "general")
                    for c in clusters[index:]
                    if c.get("cluster_id", -1) != -1
                ]
                logger.error(
                    "LLM credits exhausted — stopping extraction. "
                    "%d skill(s) already saved. Remaining clusters (%d): %s",
                    len(skills),
                    len(remaining),
                    ", ".join(remaining),
                )
                break
            except Exception as exc:
                # Discard any partially flushed rows for this cluster only;
                # previously committed skills are unaffected.
                await db.rollback()
                logger.error(
                    "Failed to extract skill for cluster '%s': %s",
                    label,
                    exc,
                )

        # Reload fresh instances — any rollback above expired the originals.
        if skill_ids:
            result = await db.execute(
                select(Skill).where(Skill.id.in_(skill_ids))
            )
            skills = list(result.scalars().all())

        logger.info("Extracted %d skills from %d clusters", len(skills), len(clusters))
        return skills
