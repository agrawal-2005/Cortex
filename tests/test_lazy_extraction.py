"""Tests for lazy extraction.

Ingestion side (cluster_and_pre_extract):
 - only the top PRE_EXTRACT_TOP_N clusters are extracted, the rest are
   stored as pending topics
 - clusters already covered by an existing skill are skipped
 - re-clustering replaces the pending snapshot instead of duplicating it
 - ingestion routes trigger the service automatically

Query side (extract_on_demand, exercised through POST /api/query/):
 - a question matching a pending cluster extracts that ONE cluster live,
   caches it (status → "extracted"), and returns the skill
 - a second identical query is answered from the cache with NO new LLM call
 - an irrelevant question returns the honest no-knowledge answer and
   never touches the LLM
 - documents outside any cluster are extracted ad hoc, exactly once

All LLM interaction is mocked at the LangChain chain level.
"""

import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from backend.config import settings
from backend.knowledge.models import (
    PendingCluster,
    Skill,
    SkillDocument,
)
from backend.processing.lazy_extraction import LazyExtractionService
from backend.processing.skill_extractor import SkillExtractionPipeline
from backend.vectorstore.store import VectorStore
from tests.conftest import TestSessionLocal
from tests.test_llm_failures import (
    VALID_RESPONSE,
    VALID_SKILL,
    seed_documents,
)

# The autouse conftest stubs replace both service entry points on the
# class (so all other tests stay offline). Capture the real
# implementations at import time — tests below restore them explicitly.
_REAL_CLUSTER_AND_PRE_EXTRACT = LazyExtractionService.cluster_and_pre_extract
_REAL_EXTRACT_ON_DEMAND = LazyExtractionService.extract_on_demand


@pytest.fixture
def real_pre_extract(monkeypatch):
    """Restore the real cluster_and_pre_extract for service-level tests."""
    monkeypatch.setattr(
        LazyExtractionService,
        "cluster_and_pre_extract",
        _REAL_CLUSTER_AND_PRE_EXTRACT,
    )


@pytest.fixture
def real_on_demand(monkeypatch):
    """Restore the real extract_on_demand for query-route tests."""
    monkeypatch.setattr(
        LazyExtractionService, "extract_on_demand", _REAL_EXTRACT_ON_DEMAND
    )


# ── Helpers ───────────────────────────────────────────────────────────────


def make_cluster(cluster_id, doc_ids, topic=None):
    return {
        "cluster_id": cluster_id,
        "topic": topic or f"topic-{cluster_id}",
        "document_ids": list(doc_ids),
        "document_count": len(doc_ids),
    }


def fake_clusterer(clusters):
    return SimpleNamespace(cluster_documents=lambda docs: clusters)


def make_service(clusters, pipeline=None):
    """Service with a scripted clusterer and a mocked bulk pipeline."""
    pipeline = pipeline or SimpleNamespace(
        extract_from_cluster=AsyncMock(return_value=None)
    )
    return LazyExtractionService(
        clusterer=fake_clusterer(clusters),
        pipeline=pipeline,
        live_pipeline=pipeline,
    )


class RecordingChain:
    """Async LangChain-chain stand-in returning a fixed response."""

    def __init__(self, response=VALID_RESPONSE):
        self.response = response
        self.calls = 0

    async def ainvoke(self, inputs):
        self.calls += 1
        return self.response


@pytest.fixture
def llm_chain(monkeypatch):
    """Intercept every real pipeline LLM call; count invocations."""
    chain = RecordingChain()
    monkeypatch.setattr(
        SkillExtractionPipeline, "_get_chain", lambda self: chain
    )
    return chain


def make_hits(*doc_ids, distance=0.5):
    """Vector-store hits above the relevance threshold (rel = 1 - d/2)."""
    return [
        {
            "id": f"doc-{did}",
            "document": f"Content for {did}",
            "distance": distance,
            "metadata": {"document_id": did, "source_type": "slack"},
        }
        for did in doc_ids
    ]


@pytest.fixture
def vector_hits(monkeypatch):
    """Make the query route's vector search return scripted hits.

    Patched on the class (like the other query tests) — patching the
    module-level instance would leave a bound-method instance attribute
    behind on monkeypatch undo, shadowing later class-level patches.
    """

    def set_hits(hits):
        monkeypatch.setattr(
            VectorStore, "search", lambda self, *a, **kw: hits
        )

    return set_hits


async def pending_rows():
    async with TestSessionLocal() as db:
        result = await db.execute(select(PendingCluster))
        return result.scalars().all()


async def seed_pending(doc_ids, topic="deploy workflow"):
    async with TestSessionLocal() as db:
        row = PendingCluster(
            cluster_id=0,
            topic=topic,
            document_ids=list(doc_ids),
            document_count=len(doc_ids),
            status="pending",
        )
        db.add(row)
        await db.commit()
        return row.id


# ── Ingestion side: pre-extract top N, store the rest as pending ──────────


class TestClusterAndPreExtract:
    @pytest.mark.asyncio
    async def test_only_top_n_extracted_rest_pending(self, real_pre_extract):
        """10 clusters → top 6 by size extracted, 4 stored as pending."""
        doc_ids = [f"d{i}" for i in range(55)]
        await seed_documents(doc_ids)

        # Cluster i has (10 - i) documents, i = 0..9; plus a noise cluster.
        clusters, start = [], 0
        for i in range(10):
            size = 10 - i
            clusters.append(make_cluster(i, doc_ids[start : start + size]))
            start += size
        clusters.append(make_cluster(-1, ["noise-doc"], topic="noise"))

        service = make_service(clusters)
        async with TestSessionLocal() as db:
            summary = await service.cluster_and_pre_extract(db)

        assert summary["clusters"] == 10  # noise excluded
        assert summary["skills_extracted"] == settings.PRE_EXTRACT_TOP_N == 6
        assert summary["pending_topics"] == 4

        extract = service.pipeline.extract_from_cluster
        assert extract.await_count == 6
        extracted_topics = {
            call.kwargs["topic_label"] for call in extract.await_args_list
        }
        assert extracted_topics == {f"topic-{i}" for i in range(6)}

        rows = await pending_rows()
        assert {r.topic for r in rows} == {f"topic-{i}" for i in range(6, 10)}
        assert all(r.status == "pending" for r in rows)
        assert all(r.document_ids for r in rows)

    @pytest.mark.asyncio
    async def test_covered_clusters_are_skipped(self, real_pre_extract):
        """A cluster mostly linked to an existing skill costs no LLM call."""
        await seed_documents(["a1", "a2", "a3", "b1", "b2", "b3"])
        async with TestSessionLocal() as db:
            skill = Skill(name="existing", description="", skill_data={})
            db.add(skill)
            await db.flush()
            for did in ("a1", "a2"):  # 2 of 3 ≥ 50% coverage
                db.add(SkillDocument(skill_id=skill.id, document_id=did))
            await db.commit()

        clusters = [
            make_cluster(0, ["a1", "a2", "a3"], topic="covered"),
            make_cluster(1, ["b1", "b2", "b3"], topic="fresh"),
        ]
        service = make_service(clusters)
        async with TestSessionLocal() as db:
            summary = await service.cluster_and_pre_extract(db)

        assert summary["already_covered"] == 1
        assert summary["skills_extracted"] == 1
        extract = service.pipeline.extract_from_cluster
        assert extract.await_count == 1
        assert extract.await_args.kwargs["topic_label"] == "fresh"

    @pytest.mark.asyncio
    async def test_rerun_replaces_pending_snapshot(self, real_pre_extract):
        """Re-clustering must not accumulate duplicate pending rows."""
        doc_ids = [f"d{i}" for i in range(8)]
        await seed_documents(doc_ids)
        clusters = [
            make_cluster(i, doc_ids[i * 2 : i * 2 + 2]) for i in range(4)
        ]

        service = make_service(clusters)
        async with TestSessionLocal() as db:
            await service.cluster_and_pre_extract(db, top_n=1)
            await service.cluster_and_pre_extract(db, top_n=1)

        rows = await pending_rows()
        assert len(rows) == 3  # replaced, not appended

    @pytest.mark.asyncio
    async def test_rerun_with_failing_extractions_replaces_snapshot(
        self, real_pre_extract
    ):
        """Extraction failures roll back the session — the pending-snapshot
        delete must survive that, or reruns duplicate every pending row
        (regression: delete ran before the loop and got rolled back)."""
        doc_ids = [f"d{i}" for i in range(8)]
        await seed_documents(doc_ids)
        clusters = [
            make_cluster(i, doc_ids[i * 2 : i * 2 + 2]) for i in range(4)
        ]

        pipeline = SimpleNamespace(
            extract_from_cluster=AsyncMock(side_effect=RuntimeError("429"))
        )
        service = make_service(clusters, pipeline=pipeline)
        async with TestSessionLocal() as db:
            first = await service.cluster_and_pre_extract(db, top_n=1)
        async with TestSessionLocal() as db:
            second = await service.cluster_and_pre_extract(db, top_n=1)

        # The failed top cluster is deferred to pending too.
        assert first["pending_topics"] == second["pending_topics"] == 4
        rows = await pending_rows()
        assert len(rows) == 4  # replaced, not appended

    @pytest.mark.asyncio
    async def test_empty_database_is_a_noop(self, real_pre_extract):
        service = make_service([])
        async with TestSessionLocal() as db:
            summary = await service.cluster_and_pre_extract(db)
        assert summary == {
            "documents": 0,
            "clusters": 0,
            "skills_extracted": 0,
            "already_covered": 0,
            "pending_topics": 0,
        }

    @pytest.mark.asyncio
    async def test_ingest_route_triggers_lazy_extraction(
        self, client, _stub_post_ingest_extraction
    ):
        """Every ingestion automatically kicks off cluster_and_pre_extract."""
        export = {
            "project": "ACME",
            "issues": [
                {
                    "key": "ACME-1",
                    "summary": "Refund fails",
                    "description": "422 on split payments",
                    "status": "Done",
                }
            ],
        }
        res = await client.post(
            "/api/ingest/jira",
            files={
                "file": (
                    "export.json",
                    io.BytesIO(json.dumps(export).encode()),
                    "application/json",
                )
            },
        )
        assert res.status_code == 200
        assert _stub_post_ingest_extraction.await_count == 1
        assert res.json()["extraction"]["pending_topics"] == 0


# ── Query side: on-demand extraction through POST /api/query/ ─────────────


@pytest.mark.usefixtures("real_on_demand")
class TestQueryOnDemandExtraction:
    @pytest.mark.asyncio
    async def test_pending_cluster_extracted_and_cached(
        self, client, vector_hits, llm_chain
    ):
        """A query hitting a pending cluster extracts it live, once."""
        await seed_documents(["alpha", "beta", "gamma"])
        await seed_pending(["alpha", "beta", "gamma"])
        vector_hits(make_hits("alpha", "beta"))

        res = await client.post(
            "/api/query/", json={"question": "How do we deploy the backend?"}
        )

        assert res.status_code == 200
        body = res.json()
        assert body["skill"]["name"] == VALID_SKILL["name"]
        assert llm_chain.calls == 1

        rows = await pending_rows()
        assert len(rows) == 1
        assert rows[0].status == "extracted"
        assert rows[0].skill_id == body["skill"]["id"]
        assert rows[0].extracted_at is not None

    @pytest.mark.asyncio
    async def test_second_identical_query_makes_no_new_llm_call(
        self, client, vector_hits, llm_chain
    ):
        """The cached skill answers repeat queries via skill_documents."""
        await seed_documents(["alpha", "beta", "gamma"])
        await seed_pending(["alpha", "beta", "gamma"])
        vector_hits(make_hits("alpha", "beta"))

        first = await client.post(
            "/api/query/", json={"question": "How do we deploy the backend?"}
        )
        assert llm_chain.calls == 1

        second = await client.post(
            "/api/query/", json={"question": "How do we deploy the backend?"}
        )

        assert second.status_code == 200
        assert llm_chain.calls == 1  # no new LLM call
        assert second.json()["skill"]["id"] == first.json()["skill"]["id"]

    @pytest.mark.asyncio
    async def test_irrelevant_query_returns_no_knowledge(
        self, client, vector_hits, llm_chain
    ):
        """Low-relevance hits → honest no-knowledge answer, LLM untouched."""
        await seed_documents(["alpha"])
        await seed_pending(["alpha"])
        # distance 1.9 → relevance 0.05, below the 0.25 threshold
        vector_hits(make_hits("alpha", distance=1.9))

        res = await client.post(
            "/api/query/", json={"question": "What is the meaning of life?"}
        )

        assert res.status_code == 200
        body = res.json()
        assert body["skill"] is None
        assert "don't have enough knowledge" in body["readable_answer"]
        assert llm_chain.calls == 0
        # The pending cluster is untouched — still available for later.
        rows = await pending_rows()
        assert rows[0].status == "pending"

    @pytest.mark.asyncio
    async def test_loose_documents_extracted_ad_hoc_exactly_once(
        self, client, vector_hits, llm_chain
    ):
        """Docs outside any cluster are extracted from the matches, and the
        SkillDocument provenance guard prevents a second extraction."""
        await seed_documents(["alpha", "beta"])  # no pending cluster
        vector_hits(make_hits("alpha", "beta"))

        first = await client.post(
            "/api/query/", json={"question": "How do we deploy the backend?"}
        )
        assert first.status_code == 200
        assert first.json()["skill"]["name"] == VALID_SKILL["name"]
        assert llm_chain.calls == 1

        second = await client.post(
            "/api/query/", json={"question": "How do we deploy the backend?"}
        )
        assert second.status_code == 200
        assert second.json()["skill"]["id"] == first.json()["skill"]["id"]
        assert llm_chain.calls == 1


# ── Concurrency guard ─────────────────────────────────────────────────────


class TestConcurrencyGuard:
    """One extraction run at a time — concurrent runs used to both see
    "cluster not covered" and extract near-identical duplicate skills."""

    @pytest.mark.asyncio
    async def test_second_bulk_run_rejected_while_first_holds_lock(
        self, real_pre_extract
    ):
        from backend.processing import lazy_extraction as le

        service = make_service([])
        async with le._extraction_lock:
            with pytest.raises(le.ExtractionInProgressError):
                await service.cluster_and_pre_extract(AsyncMock())

    @pytest.mark.asyncio
    async def test_lazy_extract_endpoint_returns_409_when_busy(
        self, client, real_pre_extract
    ):
        from backend.processing import lazy_extraction as le

        async with le._extraction_lock:
            res = await client.post("/api/v1/processing/lazy-extract")
        assert res.status_code == 409
        assert "already in progress" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_on_demand_skips_gracefully_when_busy(self, real_on_demand):
        from backend.processing import lazy_extraction as le

        service = make_service([])
        async with le._extraction_lock:
            skill = await service.extract_on_demand(
                AsyncMock(), {"doc-1": 0.9}, "topic hint"
            )
        assert skill is None  # honest fallback, cluster stays pending

    @pytest.mark.asyncio
    async def test_lock_released_after_run(self, real_pre_extract):
        from backend.processing import lazy_extraction as le

        service = make_service([])
        async with TestSessionLocal() as db:
            await service.cluster_and_pre_extract(db)  # empty DB, returns fast
            assert not le._extraction_lock.locked()
            # A follow-up run is accepted — the lock is not stuck.
            summary = await service.cluster_and_pre_extract(db)
        assert summary["documents"] == 0
