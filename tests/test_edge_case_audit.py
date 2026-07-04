"""Explicit edge-case audit: empty uploads, duplicate exports, tiny clusters.

Complements existing coverage:
- no-relevant-docs query  → test_lazy_extraction.py::test_irrelevant_query_returns_no_knowledge
- query on empty DB       → test_api_integration.py::test_query_no_results
- risky tool, no gate     → test_llm_failures.py::test_money_moving_without_gate_forces_unsafe
- auth / public health    → test_security.py (missing/invalid/revoked key, health)
"""

import pytest

from backend.processing.clustering import TopicClusterer

JIRA_EXPORT = {
    "project": "ACME",
    "issues": [
        {
            "key": "ACME-201",
            "summary": "Payment webhook retries",
            "description": "Webhook dispatcher retries 5 times with backoff.",
            "status": "Done",
        },
        {
            "key": "ACME-202",
            "summary": "Refund flow for split payments",
            "description": "Use POST /v2/refunds with split=true.",
            "status": "Done",
        },
    ],
}


class TestEmptyFileUploads:
    @pytest.mark.asyncio
    async def test_empty_json_upload_returns_400(self, client):
        res = await client.post(
            "/api/ingest/file",
            files={"file": ("empty.json", b"", "application/json")},
            data={"source_type": "custom"},
        )
        assert res.status_code == 400  # graceful error, not a 500

    @pytest.mark.asyncio
    async def test_empty_csv_upload_graceful(self, client):
        res = await client.post(
            "/api/ingest/file",
            files={"file": ("empty.csv", b"", "text/csv")},
            data={"source_type": "custom"},
        )
        assert res.status_code in (200, 400)
        if res.status_code == 200:
            assert res.json().get("documents_created", 0) == 0

    @pytest.mark.asyncio
    async def test_empty_jira_export_returns_400(self, client):
        res = await client.post(
            "/api/ingest/jira",
            files={"file": ("empty.json", b"", "application/json")},
        )
        assert res.status_code == 400


class TestDuplicateExportIdempotent:
    @pytest.mark.asyncio
    async def test_jira_export_ingested_twice_adds_nothing(self, client):
        import json

        payload = json.dumps(JIRA_EXPORT).encode()
        first = await client.post(
            "/api/ingest/jira",
            files={"file": ("export.json", payload, "application/json")},
        )
        assert first.status_code == 200
        assert first.json()["documents_ingested"] == 2

        second = await client.post(
            "/api/ingest/jira",
            files={"file": ("export.json", payload, "application/json")},
        )
        assert second.status_code == 200
        assert second.json()["documents_ingested"] == 0  # idempotent


class TestTinyClustersNotExtracted:
    def test_two_doc_topics_are_noise(self):
        """Groups smaller than min_cluster_size (3) must not become real
        clusters — so the lazy pipeline never spends an LLM call on them."""
        docs = [
            {"id": "a1", "content": "How to rotate the on-call pager schedule"},
            {"id": "a2", "content": "Rotating the pager on-call schedule steps"},
            {"id": "b1", "content": "Espresso machine cleaning instructions"},
            {"id": "b2", "content": "Cleaning the espresso machine weekly"},
        ]
        clusters = TopicClusterer().cluster_documents(docs)
        real = [c for c in clusters if c.get("cluster_id", -1) != -1]
        assert real == []  # pairs stay noise; nothing eligible for extraction
