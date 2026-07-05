"""End-to-end test for DELETE /api/workspace/data — the hard-delete cascade.

Verifies the full spec: ingest documents, extract a skill (seeded
directly — no LLM), populate BOTH ChromaDB collections (real ChromaDB,
ephemeral in-memory client), delete everything, then prove:
  - zero rows in every table (documents, skills, steps, sources,
    provenance, pending clusters, feedback, connected sources, trust)
  - zero vectors in both collections
  - a fresh query for previously-known content returns "no knowledge",
    not cached results
"""

import chromadb
import pytest

from backend.knowledge.models import (
    ApiKey,
    ConnectedSource,
    Document,
    Feedback,
    PendingCluster,
    Skill,
    SkillDocument,
    SkillStep,
    SourceTrust,
    StepSource,
)
from backend.processing.embedder import COLLECTION_NAME as DOC_COLLECTION
from backend.vectorstore.store import VectorStore
from tests.conftest import TestSessionLocal

# Captured at import time, BEFORE the conftest autouse fixture replaces it,
# so the query test can exercise the real ChromaDB search path.
_REAL_SEARCH = VectorStore.search

_QUESTION = "How do we handle enterprise refunds?"


@pytest.fixture
def ephemeral_chroma(monkeypatch):
    """Point every VectorStore at a shared in-memory ChromaDB client."""
    client = chromadb.EphemeralClient()
    monkeypatch.setattr(VectorStore, "_get_client", lambda self: client)
    # The query route caches a module-level VectorStore whose collection
    # handle may point at a previous client — reset it.
    from backend.api import routes_query

    routes_query._vector_store._client = None
    routes_query._vector_store._collection = None
    yield client
    routes_query._vector_store._client = None
    routes_query._vector_store._collection = None


async def _seed_workspace(client, doc_store: VectorStore, skill_store: VectorStore):
    """Ingest documents via the API, seed a skill with full provenance
    directly in the DB, and embed everything into ChromaDB."""
    payloads = [
        {
            "content": "Enterprise refunds over $500 need finance approval before Stripe.",
            "source_type": "slack",
            "source_id": "msg-refund-1",
            "author_name": "Sarah Chen",
            "channel_or_project": "support",
        },
        {
            "content": "Refund runbook: verify invoice, get approval, issue refund.",
            "source_type": "confluence",
            "source_id": "page-refund-runbook",
            "author_name": "Marcus Webb",
            "channel_or_project": "support-kb",
        },
    ]
    res = await client.post("/api/v1/ingest/batch", json=payloads)
    assert res.status_code == 201
    doc_ids = [d["id"] for d in res.json()]

    # Skill + steps + citations + cluster provenance + the rest of the
    # cascade surface, seeded directly (no LLM in tests).
    async with TestSessionLocal() as session:
        skill = Skill(name="Handle Enterprise Refund", description="Refund workflow")
        session.add(skill)
        await session.flush()
        step = SkillStep(skill_id=skill.id, step_order=1, action="Verify the invoice")
        session.add(step)
        await session.flush()
        session.add(StepSource(step_id=step.id, document_id=doc_ids[0], snippet="…"))
        session.add(SkillDocument(skill_id=skill.id, document_id=doc_ids[0]))
        session.add(SkillDocument(skill_id=skill.id, document_id=doc_ids[1]))
        session.add(Feedback(skill_id=skill.id, action="approve"))
        session.add(
            PendingCluster(cluster_id=1, topic="refunds", document_ids=doc_ids, document_count=2)
        )
        session.add(ConnectedSource(name="acme-slack", source_type="slack", encrypted_token="enc"))
        session.add(SourceTrust(source_identifier="Sarah Chen"))
        await session.commit()
        skill_id = skill.id

    # Embed into both real (ephemeral) collections. The fake embedding is
    # the same vector conftest gives the query, so pre-delete relevance is 1.0.
    doc_col = doc_store._get_collection()
    doc_col.upsert(
        ids=[f"doc-{d}" for d in doc_ids],
        embeddings=[[0.1] * 384 for _ in doc_ids],
        documents=[p["content"] for p in payloads],
        metadatas=[
            {"document_id": d, "source_type": p["source_type"]}
            for d, p in zip(doc_ids, payloads)
        ],
    )
    skill_store.add_skill(
        skill_id=skill_id,
        text="Handle Enterprise Refund. Refund workflow",
        embedding=[0.1] * 384,
        metadata={"title": "Handle Enterprise Refund"},
    )


async def _all_row_counts() -> dict[str, int]:
    from sqlalchemy import func, select

    counts = {}
    async with TestSessionLocal() as session:
        for model in (
            Document, Skill, SkillStep, StepSource, SkillDocument,
            PendingCluster, Feedback, ConnectedSource, SourceTrust,
        ):
            counts[model.__tablename__] = (
                await session.execute(select(func.count()).select_from(model))
            ).scalar()
    return counts


@pytest.mark.asyncio
async def test_delete_workspace_full_cascade(client, monkeypatch, ephemeral_chroma):
    monkeypatch.setattr(VectorStore, "search", _REAL_SEARCH)
    doc_store = VectorStore(collection_name=DOC_COLLECTION)
    skill_store = VectorStore()

    await _seed_workspace(client, doc_store, skill_store)

    # Sanity: data exists and is queryable BEFORE deletion.
    counts = await _all_row_counts()
    assert counts["documents"] == 2 and counts["skills"] == 1
    assert doc_store.get_collection_stats()["count"] == 2
    assert skill_store.get_collection_stats()["count"] == 1
    res = await client.post("/api/query/", json={"question": _QUESTION})
    assert res.status_code == 200
    pre = res.json()
    assert pre.get("skill") or pre.get("matched_documents"), "seeded data must be queryable"

    # ── Delete everything ──────────────────────────────────────────────
    res = await client.request(
        "DELETE", "/api/workspace/data", json={"confirm": "DELETE"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "deleted"
    assert body["deleted"]["documents"] == 2
    assert body["deleted"]["skills"] == 1
    assert body["deleted"]["document_vectors"] == 2
    assert body["deleted"]["skill_vectors"] == 1
    assert all(v == 0 for v in body["verified_remaining"].values())
    assert body["triggered_by"]["api_key_name"] == "test"
    assert body["deleted_at"]

    # ── Verify: zero rows in every table ───────────────────────────────
    assert all(v == 0 for v in (await _all_row_counts()).values())

    # ── Verify: zero vectors in both collections ───────────────────────
    assert doc_store.get_collection_stats()["count"] == 0
    assert skill_store.get_collection_stats()["count"] == 0

    # ── Fresh query returns "no knowledge", not cached results ─────────
    res = await client.post("/api/query/", json={"question": _QUESTION})
    assert res.status_code == 200
    post = res.json()
    assert post.get("skill") is None
    assert not post.get("matched_documents")
    assert "don't have enough knowledge" in post["readable_answer"]


@pytest.mark.asyncio
async def test_delete_requires_exact_confirmation(client, ephemeral_chroma):
    doc_store = VectorStore(collection_name=DOC_COLLECTION)
    skill_store = VectorStore()
    await _seed_workspace(client, doc_store, skill_store)

    for bad in ("delete", "", "DELET", "yes"):
        res = await client.request(
            "DELETE", "/api/workspace/data", json={"confirm": bad}
        )
        assert res.status_code == 400

    # Nothing was deleted.
    counts = await _all_row_counts()
    assert counts["documents"] == 2 and counts["skills"] == 1
    assert doc_store.get_collection_stats()["count"] == 2


@pytest.mark.asyncio
async def test_delete_requires_api_key(anon_client):
    res = await anon_client.request(
        "DELETE", "/api/workspace/data", json={"confirm": "DELETE"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_delete_keeps_api_keys(client, ephemeral_chroma):
    """Deleting the workspace must not lock the caller out."""
    res = await client.request(
        "DELETE", "/api/workspace/data", json={"confirm": "DELETE"}
    )
    assert res.status_code == 200

    from sqlalchemy import func, select

    async with TestSessionLocal() as session:
        keys = (
            await session.execute(select(func.count()).select_from(ApiKey))
        ).scalar()
    assert keys == 1

    # The same key still authenticates.
    res = await client.get("/api/skills/stats")
    assert res.status_code == 200
