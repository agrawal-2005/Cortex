import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.processing.skill_extractor import (
    SkillExtractionPipeline,
    _recency_weight,
    _authority_weight,
    _evidence_weight,
    _sanitize_json,
    _step_is_risky,
    _step_sources_demand_approval,
    _APPROVAL_LANGUAGE_PATTERN,
    _BASE_CONFIDENCE,
)


# ── Mock LLM response ────────────────────────────────────────────────────

MOCK_LLM_RESPONSE = json.dumps({
    "name": "Incident Response Process",
    "description": "How to handle P0 incidents in production.",
    "department": "engineering",
    "roles_involved": ["On-call engineer", "Team lead"],
    "steps": [
        {
            "step_order": 1,
            "action": "Check Grafana dashboard",
            "details": {"explanation": "Go to grafana.internal/d/api-latency", "tools": ["Grafana"]},
            "source_document_ids": ["doc-1"],
            "source_snippets": ["check the Grafana dashboard"]
        },
        {
            "step_order": 2,
            "action": "Page the on-call engineer",
            "details": {"explanation": "Use PagerDuty to escalate", "tools": ["PagerDuty"]},
            "source_document_ids": ["doc-1", "doc-2"],
            "source_snippets": ["page the on-call", "escalate via PagerDuty"]
        },
        {
            "step_order": 3,
            "action": "Write post-mortem",
            "details": {"explanation": "Document root cause within 48 hours"},
            "source_document_ids": ["doc-2"],
            "source_snippets": ["post-mortem within 48 hours"]
        }
    ],
    "edge_cases": ["If primary on-call is unavailable, escalate to secondary"],
    "conditions": ["Production incident has been detected"],
    "prerequisites": ["Access to Grafana", "PagerDuty account"]
})


def _make_mock_document(doc_id, source_type="slack", author_role="Senior Engineer", days_ago=10):
    """Create a mock Document object."""
    doc = MagicMock()
    doc.id = doc_id
    doc.content = f"Content for document {doc_id}"
    doc.source_type = source_type
    doc.source_id = f"src-{doc_id}"
    doc.channel_or_project = "engineering"
    doc.author_name = "Test User"
    doc.author_role = author_role
    doc.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    doc.ingested_at = datetime.now(timezone.utc)
    doc.source_link = None
    doc.embedding_id = None
    return doc


class TestSanitizeJson:
    def test_clean_json_passes_through(self):
        result = _sanitize_json('{"name": "test"}')
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_strips_markdown_fences(self):
        text = '```json\n{"name": "test"}\n```'
        result = _sanitize_json(text)
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_removes_trailing_commas(self):
        text = '{"items": [1, 2, 3,], "name": "test",}'
        result = _sanitize_json(text)
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_extracts_json_from_prose(self):
        text = 'Here is the result:\n{"name": "test"}\nHope this helps!'
        result = _sanitize_json(text)
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_no_json_raises_error(self):
        with pytest.raises(json.JSONDecodeError):
            _sanitize_json("No JSON here at all")


class TestRecencyWeight:
    def test_recent_document_high_weight(self):
        recent = datetime.now(timezone.utc) - timedelta(days=5)
        assert _recency_weight(recent) == 0.15

    def test_month_old_document_medium_weight(self):
        month_old = datetime.now(timezone.utc) - timedelta(days=60)
        assert _recency_weight(month_old) == 0.10

    def test_quarter_old_document_low_weight(self):
        quarter_old = datetime.now(timezone.utc) - timedelta(days=120)
        assert _recency_weight(quarter_old) == 0.05

    def test_old_document_zero_weight(self):
        old = datetime.now(timezone.utc) - timedelta(days=365)
        assert _recency_weight(old) == 0.0

    def test_none_date_zero_weight(self):
        assert _recency_weight(None) == 0.0


class TestAuthorityWeight:
    def test_director_high_weight(self):
        assert _authority_weight("Engineering Director") == 0.15

    def test_team_lead_high_weight(self):
        assert _authority_weight("Support Team Lead") == 0.15

    def test_senior_engineer_medium_weight(self):
        assert _authority_weight("Senior Engineer") == 0.12

    def test_engineer_standard_weight(self):
        assert _authority_weight("Software Engineer") == 0.08

    def test_unknown_role_minimal_weight(self):
        assert _authority_weight("Intern") == 0.04

    def test_none_role_default_weight(self):
        assert _authority_weight(None) == 0.02


class TestEvidenceWeight:
    def test_jira_highest_weight(self):
        assert _evidence_weight("jira") == 0.10

    def test_notion_medium_weight(self):
        assert _evidence_weight("notion") == 0.07

    def test_slack_low_weight(self):
        assert _evidence_weight("slack") == 0.03

    def test_unknown_source_default(self):
        assert _evidence_weight("unknown_source") == 0.02


class TestStepScoring:
    def test_step_with_no_citations_gets_base_score(self):
        pipeline = SkillExtractionPipeline()
        score = pipeline._score_step(
            {"source_document_ids": []},
            {},
            {},
        )
        assert score == _BASE_CONFIDENCE

    def test_step_with_recent_senior_jira_source(self):
        pipeline = SkillExtractionPipeline()
        doc = _make_mock_document("doc-1", source_type="jira", author_role="Team Lead", days_ago=5)
        score = pipeline._score_step(
            {"source_document_ids": ["doc-1"]},
            {"doc-1": doc},
            {},
        )
        # base(0.40) + recency(0.15) + authority(0.15) + evidence(0.10) = 0.80
        assert score >= 0.75
        assert score <= 1.0

    def test_step_with_old_slack_unknown_author(self):
        pipeline = SkillExtractionPipeline()
        doc = _make_mock_document("doc-1", source_type="slack", author_role="", days_ago=200)
        score = pipeline._score_step(
            {"source_document_ids": ["doc-1"]},
            {"doc-1": doc},
            {},
        )
        # base(0.40) + recency(0) + authority(0.02) + evidence(0.03) = 0.45
        assert score >= 0.40
        assert score < 0.55

    def test_multiple_sources_add_corroboration(self):
        pipeline = SkillExtractionPipeline()
        doc1 = _make_mock_document("doc-1", days_ago=10)
        doc2 = _make_mock_document("doc-2", days_ago=10)
        doc3 = _make_mock_document("doc-3", days_ago=10)

        score_one = pipeline._score_step(
            {"source_document_ids": ["doc-1"]},
            {"doc-1": doc1},
            {},
        )
        score_three = pipeline._score_step(
            {"source_document_ids": ["doc-1", "doc-2", "doc-3"]},
            {"doc-1": doc1, "doc-2": doc2, "doc-3": doc3},
            {},
        )
        assert score_three > score_one  # corroboration bonus

    def test_trust_scores_boost_confidence(self):
        pipeline = SkillExtractionPipeline()
        doc = _make_mock_document("doc-1", days_ago=10)

        score_no_trust = pipeline._score_step(
            {"source_document_ids": ["doc-1"]},
            {"doc-1": doc},
            {},
        )
        score_high_trust = pipeline._score_step(
            {"source_document_ids": ["doc-1"]},
            {"doc-1": doc},
            {"slack::engineering": 0.9},
        )
        assert score_high_trust > score_no_trust

    def test_confidence_capped_at_one(self):
        pipeline = SkillExtractionPipeline()
        doc = _make_mock_document("doc-1", source_type="jira", author_role="CTO", days_ago=1)
        score = pipeline._score_step(
            {"source_document_ids": ["doc-1"]},
            {"doc-1": doc},
            {"jira::engineering": 1.0},
        )
        assert score <= 1.0


class TestRiskyStepPattern:
    """Widened net: production/incident/rollback context must trip the
    approval-gate requirement even when the step is worded vaguely."""

    @pytest.mark.parametrize("action", [
        "Mitigate issue",
        "Declare P0 incident",
        "Rollback webhook dispatcher",
        "Roll back to the previous build",
        "Apply hotfix",
        "Merge-to-prod after review",
        "Deploy the service",
        "Push to production",
        "Issue a refund",
        "Delete stale records",
    ])
    def test_risky_actions_match(self, action):
        assert _step_is_risky({"action": action})

    @pytest.mark.parametrize("action", [
        "Check Grafana dashboard",
        "Write meeting notes",
        "Update the README",
    ])
    def test_benign_actions_do_not_match(self, action):
        assert not _step_is_risky({"action": action})


class TestApprovalLanguage:
    @pytest.mark.parametrize("text", [
        "create branch from main, fix, get 1 approval, merge with [HOTFIX]",
        "get approval from your lead first",
        "2 approvals per the review policy, this ships to prod",
        "this requires sign-off from finance",
        "loop in the account manager for amounts over $5000",
        "before processing the refund, verify the charge",
    ])
    def test_approval_language_matches(self, text):
        assert _APPROVAL_LANGUAGE_PATTERN.search(text)

    def test_casual_approval_mention_does_not_match(self):
        # A bare review comment ("Approval #1") is not a process requirement.
        assert not _APPROVAL_LANGUAGE_PATTERN.search(
            "[raj.patel]: Approval #1 — nice catch."
        )

    def test_step_sources_demand_approval_reads_cited_docs(self):
        doc = MagicMock()
        doc.content = "For hotfixes: get 1 approval, then merge."
        lookup = {"doc-1": doc}
        assert _step_sources_demand_approval(
            {"source_document_ids": ["doc-1"]}, lookup
        )
        assert not _step_sources_demand_approval(
            {"source_document_ids": ["missing"]}, lookup
        )
        doc.content = "Nothing procedural here."
        assert not _step_sources_demand_approval(
            {"source_document_ids": ["doc-1"]}, lookup
        )


class TestLLMCall:
    @pytest.mark.asyncio
    async def test_malformed_llm_output_triggers_retry(self):
        pipeline = SkillExtractionPipeline()

        call_count = 0
        async def mock_ainvoke(inputs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return "not valid json at all"
            return MOCK_LLM_RESPONSE

        with patch.object(pipeline, '_get_chain') as mock_chain:
            chain = MagicMock()
            chain.ainvoke = mock_ainvoke
            mock_chain.return_value = chain

            result = await pipeline._call_llm("test", [], [])
            assert result["name"] == "Incident Response Process"
            assert call_count == 3  # retried twice before succeeding

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_raises(self):
        pipeline = SkillExtractionPipeline()

        async def mock_ainvoke(inputs):
            return "garbage output with no json"

        with patch.object(pipeline, '_get_chain') as mock_chain:
            chain = MagicMock()
            chain.ainvoke = mock_ainvoke
            mock_chain.return_value = chain

            with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                await pipeline._call_llm("test", [], [])


class TestEmptyCluster:
    @pytest.mark.asyncio
    async def test_empty_document_ids_raises(self):
        pipeline = SkillExtractionPipeline()
        mock_db = AsyncMock()

        # Mock empty query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="No documents found"):
            await pipeline.extract_from_cluster(mock_db, ["nonexistent-id"], "test")
