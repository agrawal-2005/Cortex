"""Lazy skill extraction.

Extract-all proved the extraction quality but is slow and wasteful: every
cluster costs an LLM call up front, including topics nobody ever asks
about. Lazy extraction splits the work:

- **At ingestion** (``cluster_and_pre_extract``): cluster ALL documents
  (cheap — embeddings + HDBSCAN, no LLM), extract only the top
  ``PRE_EXTRACT_TOP_N`` clusters by document count, and store the rest as
  ``PendingCluster`` rows (metadata only: cluster_id, topic, document_ids).

- **At query time** (``extract_on_demand``): when relevant documents match
  no existing skill, find the pending cluster they belong to, extract that
  ONE cluster live (larger Groq model — the user is waiting), cache the
  result (status → "extracted"), and return it. A cluster is never
  extracted twice. Documents that belong to no cluster are extracted
  ad hoc from the matched documents themselves.

Clusters whose documents are already covered by an existing skill
(including repeatability-filter rejections) are skipped entirely — both
for pre-extraction and for pending storage.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.knowledge.models import (
    Document,
    PendingCluster,
    Skill,
    SkillDocument,
    SkillStep,
)
from backend.processing.clustering import TopicClusterer
from backend.processing.skill_extractor import (
    LLMCreditsExhaustedError,
    SkillExtractionPipeline,
)

logger = logging.getLogger(__name__)

# A cluster counts as "already extracted" when at least this fraction of
# its documents is linked (skill_documents) to one existing skill.
_COVERAGE_THRESHOLD = 0.5

_REJECTED_STATUS = "rejected-not-repeatable"

# One extraction run at a time, process-wide. Concurrent runs both see
# "cluster not covered yet" and extract near-identical duplicate skills
# (observed with simultaneous frontend-triggered runs) — and they compete
# for the same LLM rate-limit budget.
_extraction_lock = asyncio.Lock()


class ExtractionInProgressError(RuntimeError):
    """Another extraction run is already in progress."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LazyExtractionService:
    """Orchestrates lazy extraction at ingestion and query time."""

    def __init__(
        self,
        clusterer: TopicClusterer | None = None,
        pipeline: SkillExtractionPipeline | None = None,
        live_pipeline: SkillExtractionPipeline | None = None,
    ) -> None:
        self.clusterer = clusterer or TopicClusterer()
        # Bulk pre-extraction uses the default (cheap) model; live
        # extraction uses the larger model — the answer goes straight to
        # the waiting user.
        self.pipeline = pipeline or SkillExtractionPipeline()
        self.live_pipeline = live_pipeline or SkillExtractionPipeline(
            groq_model=settings.GROQ_LIVE_MODEL
        )

    # ── Ingestion side ────────────────────────────────────────────────

    async def cluster_and_pre_extract(
        self, db: AsyncSession, top_n: int | None = None
    ) -> dict[str, Any]:
        """Cluster every document; extract only the top clusters.

        The top ``top_n`` (default settings.PRE_EXTRACT_TOP_N) real
        clusters by document count are extracted immediately; all other
        clusters are stored as pending. Clusters already covered by an
        existing skill are skipped. Returns a summary dict.

        Raises ExtractionInProgressError when another run (bulk or
        on-demand) is already extracting.
        """
        if _extraction_lock.locked():
            raise ExtractionInProgressError(
                "A skill-extraction run is already in progress"
            )
        async with _extraction_lock:
            return await self._cluster_and_pre_extract(db, top_n)

    async def _cluster_and_pre_extract(
        self, db: AsyncSession, top_n: int | None
    ) -> dict[str, Any]:
        top_n = settings.PRE_EXTRACT_TOP_N if top_n is None else top_n

        result = await db.execute(select(Document.id, Document.content))
        rows = result.all()
        if not rows:
            return {
                "documents": 0,
                "clusters": 0,
                "skills_extracted": 0,
                "already_covered": 0,
                "pending_topics": 0,
            }

        clusters = self.clusterer.cluster_documents(
            [{"id": doc_id, "content": content} for doc_id, content in rows]
        )
        real = sorted(
            (c for c in clusters if c.get("cluster_id", -1) != -1),
            key=lambda c: -c["document_count"],
        )

        coverage = await self._coverage_map(
            db, [did for c in real for did in c["document_ids"]]
        )

        extracted = 0
        covered = 0
        pending: list[dict[str, Any]] = []
        credits_exhausted = False

        for index, cluster in enumerate(real):
            if self._is_covered(cluster, coverage):
                covered += 1
                continue
            if index >= top_n or credits_exhausted:
                pending.append(cluster)
                continue
            try:
                await self.pipeline.extract_from_cluster(
                    db=db,
                    document_ids=cluster["document_ids"],
                    topic_label=cluster["topic"],
                )
                # Commit per cluster — each skill cost an LLM call and
                # must survive failures in later clusters.
                await db.commit()
                extracted += 1
            except LLMCreditsExhaustedError:
                await db.rollback()
                logger.error(
                    "LLM credits exhausted during pre-extraction — "
                    "deferring remaining clusters to pending"
                )
                credits_exhausted = True
                pending.append(cluster)
            except Exception as exc:
                await db.rollback()
                logger.error(
                    "Pre-extraction failed for cluster '%s' — deferring "
                    "to pending: %s",
                    cluster["topic"],
                    exc,
                )
                pending.append(cluster)

        # Re-clustering invalidates the previous pending snapshot; rows
        # already extracted are kept as the cache/audit record. The delete
        # must happen HERE, after the extraction loop: extraction failures
        # roll back the session, which would silently undo an earlier
        # delete and duplicate the snapshot.
        await db.execute(
            delete(PendingCluster).where(PendingCluster.status == "pending")
        )
        for cluster in pending:
            db.add(
                PendingCluster(
                    cluster_id=cluster["cluster_id"],
                    topic=cluster["topic"],
                    document_ids=cluster["document_ids"],
                    document_count=cluster["document_count"],
                    status="pending",
                )
            )
        await db.commit()

        summary = {
            "documents": len(rows),
            "clusters": len(real),
            "skills_extracted": extracted,
            "already_covered": covered,
            "pending_topics": len(pending),
        }
        logger.info(
            "Lazy extraction: %(documents)d docs, %(clusters)d clusters — "
            "%(skills_extracted)d extracted, %(already_covered)d already "
            "covered, %(pending_topics)d pending",
            summary,
        )
        return summary

    # ── Query side ────────────────────────────────────────────────────

    async def extract_on_demand(
        self,
        db: AsyncSession,
        doc_relevance: dict[str, float],
        topic_hint: str,
        beat_relevance: float = 0.0,
    ) -> Skill | None:
        """Extract a skill live for documents that matched no skill — or
        matched an existing skill only weakly.

        ``beat_relevance`` is the best document relevance the query route
        found for an already-existing skill (0.0 when no skill matched).
        A pending cluster is only extracted when it owns a STRICTLY more
        relevant document — an existing skill with an incidental one-doc
        overlap must not shadow the pending topic the question is
        actually about, but ties keep the existing skill (no LLM spend).

        1. If the documents belong to a pending cluster that beats
           ``beat_relevance``, extract that ONE cluster, cache it
           (status → "extracted"), and return the skill.
        2. If they belong to no cluster AND no skill matched at all,
           extract ad hoc from the matched documents — unless they were
           already evaluated before (never re-extract).
        3. Returns None when nothing was extracted or the cluster was
           judged not repeatable.
        """
        if not doc_relevance:
            return None

        # Never extract concurrently with another run: both would see the
        # same uncovered documents and produce duplicate skills. Fall back
        # to the no-skill answer path — the cluster stays pending, so a
        # later query retries.
        if _extraction_lock.locked():
            logger.info(
                "Extraction already in progress — skipping on-demand "
                "extraction for this query"
            )
            return None
        async with _extraction_lock:
            cluster = await self._best_pending_cluster(
                db, doc_relevance, min_relevance=beat_relevance
            )
            if cluster is not None:
                return await self._extract_pending(db, cluster)
            if beat_relevance > 0.0:
                # An existing skill matched and no pending cluster beats
                # it — never burn an ad-hoc extraction on its documents.
                return None
            return await self._extract_loose(db, doc_relevance, topic_hint)

    async def _best_pending_cluster(
        self,
        db: AsyncSession,
        doc_relevance: dict[str, float],
        min_relevance: float = 0.0,
    ) -> PendingCluster | None:
        """The pending cluster best matching the relevant documents.

        Clusters whose best-matching document is not strictly more
        relevant than ``min_relevance`` are ignored.

        Pending clusters are few (dozens at most), so overlap is computed
        in Python rather than with JSON-array SQL that would differ
        between SQLite (tests) and Postgres.
        """
        result = await db.execute(
            select(PendingCluster).where(PendingCluster.status == "pending")
        )
        candidates = result.scalars().all()

        best: PendingCluster | None = None
        best_key: tuple[float, float] = (0.0, 0.0)
        for candidate in candidates:
            overlap = [
                doc_relevance[did]
                for did in candidate.document_ids or []
                if did in doc_relevance
            ]
            if not overlap or max(overlap) <= min_relevance:
                continue
            key = (max(overlap), sum(overlap))
            if key > best_key:
                best, best_key = candidate, key
        return best

    async def _extract_pending(
        self, db: AsyncSession, cluster: PendingCluster
    ) -> Skill | None:
        """Extract one pending cluster live and cache the result."""
        logger.info(
            "On-demand extraction of pending cluster '%s' (%d docs)",
            cluster.topic,
            cluster.document_count,
        )
        try:
            skill = await self.live_pipeline.extract_from_cluster(
                db=db,
                document_ids=list(cluster.document_ids or []),
                topic_label=cluster.topic,
            )
        except Exception as exc:
            # Extraction failed — keep the cluster pending so a later
            # query can retry.
            await db.rollback()
            logger.error(
                "On-demand extraction failed for cluster '%s': %s",
                cluster.topic,
                exc,
            )
            return None

        cluster.status = "extracted"
        cluster.skill_id = skill.id
        cluster.extracted_at = _utcnow()
        db.add(cluster)
        await db.commit()

        if skill.status == _REJECTED_STATUS:
            return None
        return await self._reload(db, skill.id)

    async def _extract_loose(
        self,
        db: AsyncSession,
        doc_relevance: dict[str, float],
        topic_hint: str,
    ) -> Skill | None:
        """Extract ad hoc from documents that belong to no cluster."""
        doc_ids = list(doc_relevance)

        # Never re-extract: if any of these documents was already part of
        # an extraction (including rejected clusters), don't burn another
        # LLM call — a matching non-rejected skill would have been found
        # by the query route already.
        result = await db.execute(
            select(SkillDocument.id)
            .where(SkillDocument.document_id.in_(doc_ids))
            .limit(1)
        )
        if result.first() is not None:
            return None

        logger.info(
            "On-demand extraction from %d loose documents (no cluster)",
            len(doc_ids),
        )
        try:
            skill = await self.live_pipeline.extract_from_cluster(
                db=db,
                document_ids=doc_ids,
                topic_label=topic_hint[:200] or "ad hoc",
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("On-demand loose-document extraction failed: %s", exc)
            return None

        if skill.status == _REJECTED_STATUS:
            return None
        return await self._reload(db, skill.id)

    # ── Helpers ───────────────────────────────────────────────────────

    async def _reload(self, db: AsyncSession, skill_id: str) -> Skill | None:
        """Reload a skill with steps/sources eagerly loaded for rendering."""
        result = await db.execute(
            select(Skill)
            .options(selectinload(Skill.steps).selectinload(SkillStep.sources))
            .where(Skill.id == skill_id)
        )
        return result.scalar_one_or_none()

    async def _coverage_map(
        self, db: AsyncSession, doc_ids: list[str]
    ) -> dict[str, dict[str, int]]:
        """Map skill_id → {document_id: 1} for all given documents."""
        if not doc_ids:
            return {}
        result = await db.execute(
            select(SkillDocument.skill_id, SkillDocument.document_id).where(
                SkillDocument.document_id.in_(doc_ids)
            )
        )
        coverage: dict[str, dict[str, int]] = defaultdict(dict)
        for skill_id, document_id in result.all():
            coverage[skill_id][document_id] = 1
        return coverage

    @staticmethod
    def _is_covered(
        cluster: dict[str, Any], coverage: dict[str, dict[str, int]]
    ) -> bool:
        """True if one existing skill already covers most of the cluster."""
        doc_ids = set(cluster["document_ids"])
        if not doc_ids or not coverage:
            return False
        best = max(
            (len(doc_ids & set(docs)) for docs in coverage.values()),
            default=0,
        )
        return best >= _COVERAGE_THRESHOLD * len(doc_ids)
