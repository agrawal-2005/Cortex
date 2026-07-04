"""Query → skill matching via cluster-level provenance (skill_documents).

Covers the fix for the "no skill found" problem: skills only cite a few
document IDs in step_sources, so matching query hits against step_sources
alone misses most documents. The query route now matches against
skill_documents (every doc in the source cluster) first, falling back to
step_sources for legacy skills.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from backend.knowledge.models import (
    Document,
    Skill,
    SkillDocument,
    SkillStep,
    StepSource,
)
from backend.vectorstore.store import VectorStore
from tests.conftest import TestSessionLocal


def _hit(doc_id: str, distance: float = 0.2) -> dict:
    return {
        "id": f"doc-{doc_id}",
        "metadata": {"document_id": doc_id, "source_type": "github"},
        "document": f"content of {doc_id}",
        "distance": distance,
    }


async def _seed_document(db, doc_id: str) -> Document:
    doc = Document(
        id=doc_id,
        content=f"content of {doc_id}",
        source_type="github",
        source_id=f"src-{doc_id}",
    )
    db.add(doc)
    return doc


async def _seed_skill(db, name: str, confidence: float = 0.7) -> Skill:
    skill = Skill(
        id=str(uuid.uuid4()),
        name=name,
        description=f"How we {name}",
        confidence=confidence,
        status="draft",
        skill_data={},
    )
    db.add(skill)
    return skill


@pytest.mark.asyncio
async def test_query_finds_skill_via_skill_documents(client, monkeypatch):
    """A doc NOT cited in step_sources still resolves to its cluster's skill."""
    doc_id = str(uuid.uuid4())
    async with TestSessionLocal() as db:
        await _seed_document(db, doc_id)
        skill = await _seed_skill(db, "deploy to production")
        # Cluster provenance link only — deliberately NO StepSource.
        db.add(SkillDocument(skill_id=skill.id, document_id=doc_id))
        await db.commit()
        skill_name = skill.name

    monkeypatch.setattr(VectorStore, "search", lambda self, *a, **kw: [_hit(doc_id)])

    res = await client.post("/api/query/", json={"question": "How do we deploy?"})
    assert res.status_code == 200
    data = res.json()
    assert data["skill"] is not None
    assert data["skill"]["name"] == skill_name
    assert data["source_hits"][0]["document_id"] == doc_id


@pytest.mark.asyncio
async def test_query_falls_back_to_step_sources_for_legacy_skills(
    client, monkeypatch
):
    """Skills extracted before skill_documents existed still match."""
    doc_id = str(uuid.uuid4())
    async with TestSessionLocal() as db:
        await _seed_document(db, doc_id)
        skill = await _seed_skill(db, "legacy incident response")
        step = SkillStep(
            id=str(uuid.uuid4()),
            skill_id=skill.id,
            step_order=1,
            action="check dashboard",
        )
        db.add(step)
        db.add(
            StepSource(
                id=str(uuid.uuid4()),
                step_id=step.id,
                document_id=doc_id,
            )
        )
        await db.commit()
        skill_name = skill.name

    monkeypatch.setattr(VectorStore, "search", lambda self, *a, **kw: [_hit(doc_id)])

    res = await client.post("/api/query/", json={"question": "incident?"})
    assert res.status_code == 200
    data = res.json()
    assert data["skill"] is not None
    assert data["skill"]["name"] == skill_name


@pytest.mark.asyncio
async def test_query_ranks_skill_with_most_matching_documents(client, monkeypatch):
    """The skill whose cluster overlaps the most hits wins, even at lower confidence."""
    doc_a, doc_b, doc_c = (str(uuid.uuid4()) for _ in range(3))
    async with TestSessionLocal() as db:
        for did in (doc_a, doc_b, doc_c):
            await _seed_document(db, did)
        skill_one = await _seed_skill(db, "one-doc skill", confidence=0.95)
        skill_two = await _seed_skill(db, "two-doc skill", confidence=0.5)
        db.add(SkillDocument(skill_id=skill_one.id, document_id=doc_a))
        db.add(SkillDocument(skill_id=skill_two.id, document_id=doc_b))
        db.add(SkillDocument(skill_id=skill_two.id, document_id=doc_c))
        await db.commit()

    monkeypatch.setattr(
        VectorStore,
        "search",
        lambda self, *a, **kw: [_hit(doc_a), _hit(doc_b), _hit(doc_c)],
    )

    res = await client.post("/api/query/", json={"question": "which skill?"})
    assert res.status_code == 200
    assert res.json()["skill"]["name"] == "two-doc skill"


@pytest.mark.asyncio
async def test_query_prefers_strong_match_over_big_weak_cluster(client, monkeypatch):
    """One highly relevant doc beats a large cluster of weakly relevant ones."""
    doc_strong, doc_w1, doc_w2 = (str(uuid.uuid4()) for _ in range(3))
    async with TestSessionLocal() as db:
        for did in (doc_strong, doc_w1, doc_w2):
            await _seed_document(db, did)
        focused = await _seed_skill(db, "focused skill", confidence=0.5)
        broad = await _seed_skill(db, "broad skill", confidence=0.9)
        db.add(SkillDocument(skill_id=focused.id, document_id=doc_strong))
        db.add(SkillDocument(skill_id=broad.id, document_id=doc_w1))
        db.add(SkillDocument(skill_id=broad.id, document_id=doc_w2))
        await db.commit()

    # strong hit: distance 0.2 -> relevance 0.9; weak hits: 1.2 -> 0.4
    monkeypatch.setattr(
        VectorStore,
        "search",
        lambda self, *a, **kw: [
            _hit(doc_strong, distance=0.2),
            _hit(doc_w1, distance=1.2),
            _hit(doc_w2, distance=1.2),
        ],
    )

    res = await client.post("/api/query/", json={"question": "specific thing?"})
    assert res.status_code == 200
    assert res.json()["skill"]["name"] == "focused skill"


@pytest.mark.asyncio
async def test_query_legacy_step_source_skill_beats_weaker_cluster_match(
    client, monkeypatch
):
    """A legacy skill (provenance only in step_sources) that owns the MOST
    relevant hit must beat a skill_documents skill with a weaker hit.
    Previously any skill_documents match early-returned, so legacy skills
    could never win (proxy/badge/benchmark queries all misrouted)."""
    doc_strong, doc_weak = str(uuid.uuid4()), str(uuid.uuid4())
    async with TestSessionLocal() as db:
        await _seed_document(db, doc_strong)
        await _seed_document(db, doc_weak)
        legacy = await _seed_skill(db, "configure socks proxy", confidence=0.55)
        step = SkillStep(
            id=str(uuid.uuid4()),
            skill_id=legacy.id,
            step_order=1,
            action="set the proxy env var",
        )
        db.add(step)
        db.add(
            StepSource(
                id=str(uuid.uuid4()), step_id=step.id, document_id=doc_strong
            )
        )
        big_cluster = await _seed_skill(db, "dev environment setup", confidence=0.9)
        db.add(SkillDocument(skill_id=big_cluster.id, document_id=doc_weak))
        await db.commit()

    # strong: distance 0.2 -> relevance 0.9; weak: 1.2 -> 0.4
    monkeypatch.setattr(
        VectorStore,
        "search",
        lambda self, *a, **kw: [
            _hit(doc_strong, distance=0.2),
            _hit(doc_weak, distance=1.2),
        ],
    )

    res = await client.post("/api/query/", json={"question": "configure proxy?"})
    assert res.status_code == 200
    assert res.json()["skill"]["name"] == "configure socks proxy"


@pytest.mark.asyncio
async def test_query_skill_similarity_breaks_document_near_ties(client, monkeypatch):
    """When two skills own hits of similar relevance, the skill whose
    name/description semantically matches the question wins — even if the
    other skill's doc scores marginally higher. Encodes the live bug:
    'How to report vulnerabilities?' hit a TUI-dialog PR at 0.51 and the
    pentest-report cluster at 0.47, so the TUI skill misrouted the query."""
    from backend.processing.embeddings import EmbeddingService

    doc_tui, doc_pentest = str(uuid.uuid4()), str(uuid.uuid4())
    async with TestSessionLocal() as db:
        await _seed_document(db, doc_tui)
        await _seed_document(db, doc_pentest)
        tui = await _seed_skill(db, "sanitize text in TUI", confidence=0.9)
        pentest = await _seed_skill(db, "generate pentest report", confidence=0.5)
        db.add(SkillDocument(skill_id=tui.id, document_id=doc_tui))
        db.add(SkillDocument(skill_id=pentest.id, document_id=doc_pentest))
        await db.commit()

    # Question embedding aligns with the pentest skill's text, is
    # orthogonal to the TUI skill's text.
    q_vec = [1.0] + [0.0] * 383
    tui_vec = [0.0, 1.0] + [0.0] * 382

    def fake_embed(self, text):
        return q_vec  # the question itself

    def fake_embed_batch(self, texts):
        return [q_vec if "pentest" in t.lower() else tui_vec for t in texts]

    monkeypatch.setattr(EmbeddingService, "generate_embedding", fake_embed)
    monkeypatch.setattr(EmbeddingService, "generate_embeddings", fake_embed_batch)

    # TUI doc slightly MORE relevant (0.51 vs 0.47) — sim must outweigh it.
    monkeypatch.setattr(
        VectorStore,
        "search",
        lambda self, *a, **kw: [
            _hit(doc_tui, distance=0.98),      # relevance 0.51
            _hit(doc_pentest, distance=1.06),  # relevance 0.47
        ],
    )

    res = await client.post(
        "/api/query/", json={"question": "How to report vulnerabilities?"}
    )
    assert res.status_code == 200
    assert res.json()["skill"]["name"] == "generate pentest report"


@pytest.mark.asyncio
async def test_query_orphan_vector_hits_return_plain_no_match(client, monkeypatch):
    """Vector hits whose document IDs have no Document row (stale
    embeddings) must yield the plain no-match answer — never
    'Here are the most relevant documents:' with zero documents."""
    orphan_id = str(uuid.uuid4())  # deliberately NOT seeded in the DB

    monkeypatch.setattr(
        VectorStore, "search", lambda self, *a, **kw: [_hit(orphan_id)]
    )

    res = await client.post("/api/query/", json={"question": "deployment?"})
    assert res.status_code == 200
    data = res.json()
    assert data["skill"] is None
    assert data["matched_documents"] == []
    assert "most relevant documents" not in data["readable_answer"]
    assert data["readable_answer"].startswith(
        "I don't have enough knowledge to answer that question yet."
    )


@pytest.mark.asyncio
async def test_query_no_skill_returns_matched_documents(client, monkeypatch):
    """Docs match but no skill exists — return the documents themselves
    with preview/link/author/relevance plus an extraction suggestion."""
    doc_id = str(uuid.uuid4())
    async with TestSessionLocal() as db:
        db.add(
            Document(
                id=doc_id,
                content="Pin dependency versions in requirements.txt " + "x" * 300,
                source_type="github_pr",
                source_id=f"src-{doc_id}",
                source_link="https://github.com/owner/repo/pull/42",
                author_name="sarah",
            )
        )
        await db.commit()

    # distance 0.36 -> relevance 0.82
    monkeypatch.setattr(
        VectorStore, "search", lambda self, *a, **kw: [_hit(doc_id, distance=0.36)]
    )

    res = await client.post("/api/query/", json={"question": "dependency pinning?"})
    assert res.status_code == 200
    data = res.json()
    assert data["skill"] is None
    assert data["readable_answer"] == (
        "No structured workflow exists for this topic yet. "
        "Here are the most relevant documents:"
    )
    assert "Run skill extraction" in data["suggestion"]

    assert len(data["matched_documents"]) == 1
    doc = data["matched_documents"][0]
    assert doc["preview"].startswith("Pin dependency versions")
    assert len(doc["preview"]) == 200
    assert doc["source_type"] == "github_pr"
    assert doc["source_link"] == "https://github.com/owner/repo/pull/42"
    assert doc["author"] == "sarah"
    assert doc["relevance"] == pytest.approx(0.82, abs=0.001)


@pytest.mark.asyncio
async def test_query_matched_documents_sorted_by_relevance(client, monkeypatch):
    doc_a, doc_b = str(uuid.uuid4()), str(uuid.uuid4())
    async with TestSessionLocal() as db:
        await _seed_document(db, doc_a)
        await _seed_document(db, doc_b)
        await db.commit()

    monkeypatch.setattr(
        VectorStore,
        "search",
        lambda self, *a, **kw: [_hit(doc_a, distance=1.0), _hit(doc_b, distance=0.2)],
    )

    res = await client.post("/api/query/", json={"question": "anything?"})
    assert res.status_code == 200
    matched = res.json()["matched_documents"]
    assert [m["relevance"] for m in matched] == sorted(
        (m["relevance"] for m in matched), reverse=True
    )
    assert matched[0]["preview"] == f"content of {doc_b}"


@pytest.mark.asyncio
async def test_extract_from_cluster_links_all_cluster_documents():
    """Extraction writes skill_documents rows for EVERY doc in the cluster,
    not just the ones the LLM cited."""
    from sqlalchemy import select

    from backend.processing.skill_extractor import SkillExtractionPipeline

    doc_ids = [str(uuid.uuid4()) for _ in range(4)]
    async with TestSessionLocal() as db:
        for did in doc_ids:
            await _seed_document(db, did)
        await db.commit()

    # LLM cites only the first document.
    parsed = {
        "name": "Test Skill",
        "description": "desc",
        "department": "engineering",
        "steps": [
            {
                "step_order": i,
                "action": f"step {i}",
                "details": {},
                "source_document_ids": [doc_ids[0]],
                "source_snippets": ["snippet"],
            }
            for i in range(1, 4)
        ],
    }

    pipeline = SkillExtractionPipeline()
    async with TestSessionLocal() as db:
        with patch.object(pipeline, "_call_llm", AsyncMock(return_value=parsed)):
            skill = await pipeline.extract_from_cluster(
                db, doc_ids, topic_label="test topic"
            )
        await db.commit()
        skill_id = skill.id

    async with TestSessionLocal() as db:
        rows = (
            await db.execute(
                select(SkillDocument.document_id).where(
                    SkillDocument.skill_id == skill_id
                )
            )
        ).scalars().all()

    assert sorted(rows) == sorted(doc_ids)
