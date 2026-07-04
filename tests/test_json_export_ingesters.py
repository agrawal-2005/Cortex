"""Tests for the Jira and Confluence JSON export ingesters."""

from datetime import datetime

import pytest

from backend.ingestion.confluence_json_ingester import ConfluenceJsonIngester
from backend.ingestion.jira_json_ingester import JiraJsonIngester


# ── Jira ──────────────────────────────────────────────────────────────────


@pytest.fixture
def jira_export():
    return {
        "project": "ACME",
        "export_date": "2026-06-15",
        "issues": [
            {
                "key": "ACME-101",
                "summary": "Refund fails for split payments",
                "description": "Refund API returns 422 when the order was paid "
                "with two cards.",
                "status": "Done",
                "issue_type": "Bug",
                "priority": "High",
                "assignee": "Priya Sharma",
                "reporter": "Marcus Lee",
                "created": "2026-06-01T09:00:00Z",
                "updated": "2026-06-03T17:30:00Z",
                "labels": ["billing", "refunds"],
                "resolution": "Fixed",
                "comments": [
                    {
                        "author": "Priya Sharma",
                        "body": "Use POST /v2/refunds with split=true.",
                        "created": "2026-06-02T10:00:00Z",
                    },
                    {"author": "Marcus Lee", "body": "", "created": ""},
                ],
            },
            {"key": "ACME-102", "summary": ""},  # skipped: no summary
            "not-a-dict",  # skipped
        ],
    }


class TestJiraJsonIngester:
    @pytest.mark.asyncio
    async def test_parses_issues_and_skips_invalid(self, jira_export):
        ingester = JiraJsonIngester()
        docs = await ingester.parse_export(jira_export)
        assert len(docs) == 1
        assert ingester.stats == {"issues": 1, "comments": 1, "skipped": 2}

    @pytest.mark.asyncio
    async def test_document_fields(self, jira_export):
        docs = await JiraJsonIngester().parse_export(jira_export)
        doc = docs[0]
        assert doc.source_type == "jira"
        assert doc.source_id == "ACME-101"
        assert doc.source_link == "https://acmetech.atlassian.net/browse/ACME-101"
        assert doc.channel_or_project == "ACME"
        assert doc.author_name == "Marcus Lee"
        # naive UTC from the `updated` timestamp
        assert doc.created_at == datetime(2026, 6, 3, 17, 30)
        assert doc.created_at.tzinfo is None

    @pytest.mark.asyncio
    async def test_content_includes_metadata_and_comments(self, jira_export):
        docs = await JiraJsonIngester().parse_export(jira_export)
        content = docs[0].content
        assert "[ACME-101] Refund fails for split payments" in content
        assert "Priority: High" in content
        assert "Labels: billing, refunds" in content
        assert "Resolution: Fixed" in content
        # comments quoted with author, verbatim body preserved
        assert "Comment by Priya Sharma" in content
        assert "POST /v2/refunds with split=true" in content

    @pytest.mark.asyncio
    async def test_accepts_bare_list(self, jira_export):
        docs = await JiraJsonIngester().parse_export(jira_export["issues"])
        assert len(docs) == 1

    @pytest.mark.asyncio
    async def test_rejects_wrong_shape(self):
        with pytest.raises(ValueError, match="issues"):
            await JiraJsonIngester().parse_export({"pages": []})


# ── Confluence ────────────────────────────────────────────────────────────


@pytest.fixture
def confluence_export():
    return {
        "space_export": "ACME",
        "export_date": "2026-06-15",
        "pages": [
            {
                "id": 10003,
                "title": "Refund Policy",
                "space": "SUPPORT",
                "body": "Refunds over $500 require manager approval.",
                "author": "Dana Wu",
                "created": "2025-09-01T08:00:00Z",
                "last_modified": "2026-05-10T12:00:00Z",
                "url": "https://acmetech.atlassian.net/wiki/spaces/SUPPORT/pages/10003",
            },
            {"id": "10004", "title": "Empty", "body": ""},  # skipped: no body
        ],
    }


class TestConfluenceJsonIngester:
    @pytest.mark.asyncio
    async def test_parses_pages_and_skips_invalid(self, confluence_export):
        ingester = ConfluenceJsonIngester()
        docs = await ingester.parse_export(confluence_export)
        assert len(docs) == 1
        assert ingester.stats == {"pages": 1, "skipped": 1}

    @pytest.mark.asyncio
    async def test_document_fields(self, confluence_export):
        docs = await ConfluenceJsonIngester().parse_export(confluence_export)
        doc = docs[0]
        assert doc.source_type == "confluence"
        assert doc.source_id == "10003"  # coerced to str
        assert doc.source_label == "Refund Policy"
        assert doc.channel_or_project == "SUPPORT"
        assert doc.author_name == "Dana Wu"
        assert doc.source_link.endswith("/pages/10003")
        # created_at prefers last_modified, stored naive UTC
        assert doc.created_at == datetime(2026, 5, 10, 12, 0)
        assert doc.created_at.tzinfo is None

    @pytest.mark.asyncio
    async def test_content_includes_title_space_body(self, confluence_export):
        docs = await ConfluenceJsonIngester().parse_export(confluence_export)
        content = docs[0].content
        assert "Refund Policy" in content
        assert "Space: SUPPORT" in content
        assert "Refunds over $500 require manager approval." in content

    @pytest.mark.asyncio
    async def test_accepts_bare_list(self, confluence_export):
        docs = await ConfluenceJsonIngester().parse_export(
            confluence_export["pages"]
        )
        assert len(docs) == 1

    @pytest.mark.asyncio
    async def test_rejects_wrong_shape(self):
        with pytest.raises(ValueError, match="pages"):
            await ConfluenceJsonIngester().parse_export({"issues": []})
