"""Unit tests for GitHubIngester budget/rate-limit resilience."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.ingestion.github_ingester import GitHubIngester


def _response(payload, status_code=200, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


def _issue(number, title, is_pr=False):
    item = {
        "number": number,
        "title": title,
        "body": f"body of {number}",
        "html_url": f"https://github.com/o/r/issues/{number}",
        "user": {"login": "sarah"},
        "created_at": "2026-05-01T10:00:00Z",
    }
    if is_pr:
        item["pull_request"] = {"url": "..."}
    return item


@pytest.mark.asyncio
async def test_issue_docs_survive_budget_exhaustion_during_comments():
    """When the budget runs out mid-comment-fetching, every paginated
    issue/PR must still become a document (without comments)."""
    # Budget of 1: the /issues page consumes it; the first comments call
    # then raises RateLimitExhausted from the budget check.
    ingester = GitHubIngester("o/r", max_requests=1, include_comments=True)
    ingester._client = MagicMock()
    ingester._client.get = AsyncMock(
        return_value=_response([_issue(1, "bug"), _issue(2, "feature", is_pr=True)])
    )

    docs = await ingester._fetch_issues_and_prs()

    assert len(docs) == 2
    assert {d.source_type for d in docs} == {"github_issue", "github_pr"}
    assert "--- Comments ---" not in docs[0].content
    assert ingester.stats["rate_limited"] is True
    assert ingester.stats["issues"] == 1
    assert ingester.stats["prs"] == 1


@pytest.mark.asyncio
async def test_paginate_keeps_collected_pages_on_rate_limit():
    """Mid-pagination budget exhaustion returns the pages already fetched."""
    ingester = GitHubIngester("o/r", max_requests=1)
    ingester._client = MagicMock()
    page1 = _response(
        [_issue(1, "one")],
        headers={"Link": '<https://api.github.com/x?page=2>; rel="next"'},
    )
    ingester._client.get = AsyncMock(return_value=page1)

    items = await ingester._paginate("/repos/o/r/issues")

    assert len(items) == 1
    assert ingester.stats["rate_limited"] is True


@pytest.mark.asyncio
async def test_fetch_documents_returns_partials_from_all_fetchers():
    """End to end: docs fetched first, then issues partially — nothing lost."""
    # Budget walk-through: readme(1) + CONTRIBUTING 404s(2,3) + docs/ 404(4)
    # + issues page(5); the comments call then exhausts the budget.
    ingester = GitHubIngester(
        "o/r", max_requests=5, include_comments=True, max_doc_files=0
    )
    ingester._client = MagicMock()

    readme = _response({"encoding": "base64", "content": "IyBIZWxsbw=="})  # "# Hello"
    issues = _response([_issue(1, "bug")])
    not_found = _response(None, status_code=404)

    responses = {
        "/repos/o/r/readme": readme,
        "/repos/o/r/issues": issues,
    }

    async def fake_get(path, params=None):
        return responses.get(path, not_found)

    ingester._client.get = AsyncMock(side_effect=fake_get)

    docs = await ingester.fetch_documents()

    types = [d.source_type for d in docs]
    assert "github_doc" in types
    assert "github_issue" in types
