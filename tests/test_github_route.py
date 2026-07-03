import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.schemas import DocumentCreate
from tests.conftest import TestSessionLocal


@pytest.mark.asyncio
async def test_github_route_rejects_bad_repo(client):
    response = await client.post("/api/ingest/github", json={"repo": "not-a-repo"})
    # schema-level validation rejects malformed owner/repo with 422
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_github_route_with_mocked_ingester(client):
    mock_ingester = MagicMock()
    mock_ingester.stats = {"issues": 1, "requests_used": 3}
    mock_ingester.ingest = AsyncMock(return_value=[
        DocumentCreate(
            content="Issue #1: broken build",
            source_type="github_issue",
            source_id="owner/repo#1",
            source_link="https://github.com/owner/repo/issues/1",
            channel_or_project="owner/repo",
            author_name="sarah",
        )
    ])
    with (
        patch("backend.api.routes_ingest.GitHubIngester", return_value=mock_ingester),
        patch("backend.api.routes_ingest.async_session_factory", TestSessionLocal),
    ):
        response = await client.post("/api/ingest/github", json={"repo": "owner/repo"})
        assert response.status_code == 202
        task_id = response.json()["task_id"]

        # The ingestion now runs as a background asyncio task — poll until done.
        status = None
        for _ in range(100):
            await asyncio.sleep(0.01)
            resp = await client.get("/api/ingest/status", params={"task_id": task_id})
            status = resp.json()
            if status["status"] in ("completed", "failed"):
                break

    assert status["status"] == "completed"
    assert status["progress"]["documents_ingested"] == 1
    assert status["progress"]["stats"]["issues"] == 1

    listing = await client.get("/api/v1/ingest/documents")
    assert any(d["source_type"] == "github_issue" for d in listing.json())
