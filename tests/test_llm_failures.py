"""Tests for every way the LLM can fail during skill extraction.

Covers:
 1. Empty response            → retry 3x, then skip the cluster
 2. Invalid JSON (truncated)  → JSON repair, then retry
 3. Markdown-fenced JSON      → fences stripped, parsed
 4. Prose around JSON         → JSON extracted from the middle
 5. Wrong schema (no "steps") → reject + retry with stricter prompt
 6. Timeout (> 60s)           → abort, move to next cluster
 7. HTTP 429 rate limit       → exponential backoff, retry
 8. HTTP 402 credits gone     → stop gracefully, keep saved skills,
                                report remaining clusters
 9. HTTP 500 server error     → retry 3x with backoff
10. Skill with 0 steps        → reject (minimum 3 steps required)

Every LLM interaction is mocked at the LangChain chain level — no real
HuggingFace calls are made.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from backend.knowledge.models import Document, Skill
from backend.processing import skill_extractor
from backend.processing.skill_extractor import (
    LLMCreditsExhaustedError,
    LLMTimeoutError,
    MIN_SKILL_STEPS,
    SchemaValidationError,
    SkillExtractionPipeline,
    STRICT_FORMAT_REMINDER,
    _sanitize_json,
    _validate_skill_schema,
)
from tests.conftest import TestSessionLocal

LOGGER_NAME = "backend.processing.skill_extractor"


# ── Fixtures & helpers ────────────────────────────────────────────────────

VALID_SKILL = {
    "name": "Deploy Backend Service",
    "description": "How to deploy the backend to production.",
    "department": "engineering",
    "roles_involved": ["Engineer"],
    "steps": [
        {
            "step_order": 1,
            "action": "Run the test suite",
            "details": {"explanation": "pytest must pass"},
            "source_document_ids": ["alpha"],
            "source_snippets": ["run pytest first"],
        },
        {
            "step_order": 2,
            "action": "Build the Docker image",
            "details": {"explanation": "docker build ."},
            "source_document_ids": ["alpha"],
            "source_snippets": ["build the image"],
        },
        {
            "step_order": 3,
            "action": "Deploy to production",
            "details": {"explanation": "kubectl rollout"},
            "source_document_ids": ["beta"],
            "source_snippets": ["rollout restart"],
        },
    ],
    "edge_cases": ["Rollback if health checks fail"],
    "conditions": ["CI is green"],
    "prerequisites": ["kubectl access"],
}
VALID_RESPONSE = json.dumps(VALID_SKILL)


class FakeHTTPError(Exception):
    """Mimics huggingface_hub.HfHubHTTPError: message + .response.status_code."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.response = SimpleNamespace(status_code=status_code)


def make_pipeline(responses):
    """Build a pipeline whose chain returns/raises scripted responses.

    ``responses`` items may be: a str (returned), an Exception (raised), or
    an async callable (awaited — used to simulate slow responses).  The last
    item repeats forever.  Returns (pipeline, calls) where ``calls`` records
    the call count and every user_prompt sent.
    """
    pipeline = SkillExtractionPipeline()
    calls = {"count": 0, "prompts": []}

    async def fake_ainvoke(inputs):
        item = responses[min(calls["count"], len(responses) - 1)]
        calls["count"] += 1
        calls["prompts"].append(inputs["user_prompt"])
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return await item()
        return item

    chain = MagicMock()
    chain.ainvoke = fake_ainvoke
    pipeline._chain = chain  # _get_chain() returns this, never builds a real LLM
    return pipeline, calls


@pytest.fixture
def no_sleep(monkeypatch):
    """Replace retry/backoff sleeps with a recording mock (keeps tests fast)."""
    mock = AsyncMock()
    monkeypatch.setattr(skill_extractor, "_sleep", mock)
    return mock


async def seed_documents(doc_ids):
    """Insert real Document rows into the test DB."""
    async with TestSessionLocal() as session:
        for did in doc_ids:
            session.add(
                Document(
                    id=did,
                    content=f"Content for {did}",
                    source_type="slack",
                    source_id=f"src-{did}",
                    channel_or_project="engineering",
                    author_name="Test User",
                    author_role="Senior Engineer",
                    # naive UTC — matches production convention
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
        await session.commit()


def make_clusters(*doc_id_groups):
    return [
        {"cluster_id": i, "label": f"cluster-{i}", "document_ids": list(ids)}
        for i, ids in enumerate(doc_id_groups)
    ]


async def count_skills_in_db():
    """Count committed skills using a *fresh* session (proves durability)."""
    async with TestSessionLocal() as session:
        result = await session.execute(select(Skill))
        return len(list(result.scalars().all()))


# ── 1. Empty response ─────────────────────────────────────────────────────

class TestEmptyResponse:
    @pytest.mark.asyncio
    async def test_retried_three_times_then_fails(self, no_sleep, caplog):
        pipeline, calls = make_pipeline([""])
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                await pipeline._call_llm("test", [], [])
        assert calls["count"] == 3
        assert "Empty LLM response" in caplog.text

    @pytest.mark.asyncio
    async def test_whitespace_only_treated_as_empty(self, no_sleep):
        pipeline, calls = make_pipeline(["   \n\t  "])
        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            await pipeline._call_llm("test", [], [])
        assert calls["count"] == 3

    @pytest.mark.asyncio
    async def test_recovers_if_later_attempt_succeeds(self, no_sleep):
        pipeline, calls = make_pipeline(["", VALID_RESPONSE])
        result = await pipeline._call_llm("test", [], [])
        assert result["name"] == VALID_SKILL["name"]
        assert calls["count"] == 2

    @pytest.mark.asyncio
    async def test_cluster_skipped_not_crashed(self, no_sleep, caplog):
        """Empty responses for cluster 0; cluster 1 succeeds anyway."""
        await seed_documents(["alpha", "beta", "gamma"])
        # cluster 0 burns 3 attempts on "", cluster 1 gets valid JSON
        pipeline, calls = make_pipeline(["", "", "", VALID_RESPONSE])
        clusters = make_clusters(["alpha", "beta"], ["gamma"])

        async with TestSessionLocal() as db:
            with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
                skills = await pipeline.extract_all_clusters(db, clusters)

        assert len(skills) == 1
        assert "Failed to extract skill for cluster 'cluster-0'" in caplog.text
        assert await count_skills_in_db() == 1  # partial result committed


# ── 2. Invalid JSON (missing closing brace) ───────────────────────────────

class TestInvalidJson:
    def test_sanitize_repairs_missing_closing_brace(self):
        truncated = VALID_RESPONSE[:-1]  # drop final "}"
        parsed = json.loads(_sanitize_json(truncated))
        assert parsed["name"] == VALID_SKILL["name"]
        assert len(parsed["steps"]) == 3

    def test_sanitize_repairs_multiple_missing_closers(self):
        truncated = '{"name": "x", "steps": [{"action": "do"'
        parsed = json.loads(_sanitize_json(truncated))
        assert parsed["steps"][0]["action"] == "do"

    @pytest.mark.asyncio
    async def test_repaired_json_needs_no_retry(self, no_sleep):
        pipeline, calls = make_pipeline([VALID_RESPONSE[:-1]])
        result = await pipeline._call_llm("test", [], [])
        assert result["name"] == VALID_SKILL["name"]
        assert calls["count"] == 1  # repair succeeded, no retry needed

    @pytest.mark.asyncio
    async def test_unrepairable_json_triggers_retry(self, no_sleep, caplog):
        pipeline, calls = make_pipeline(['{"name": broken', VALID_RESPONSE])
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            result = await pipeline._call_llm("test", [], [])
        assert result["name"] == VALID_SKILL["name"]
        assert calls["count"] == 2
        assert "JSON parse error" in caplog.text


# ── 3. Markdown fences ────────────────────────────────────────────────────

class TestMarkdownFences:
    @pytest.mark.asyncio
    async def test_fenced_json_parsed_first_try(self, no_sleep):
        pipeline, calls = make_pipeline([f"```json\n{VALID_RESPONSE}\n```"])
        result = await pipeline._call_llm("test", [], [])
        assert result["name"] == VALID_SKILL["name"]
        assert calls["count"] == 1

    @pytest.mark.asyncio
    async def test_bare_fences_without_language_tag(self, no_sleep):
        pipeline, calls = make_pipeline([f"```\n{VALID_RESPONSE}\n```"])
        result = await pipeline._call_llm("test", [], [])
        assert len(result["steps"]) == 3
        assert calls["count"] == 1


# ── 4. Prose around the JSON ──────────────────────────────────────────────

class TestProseAroundJson:
    @pytest.mark.asyncio
    async def test_json_extracted_from_middle(self, no_sleep):
        wrapped = (
            "Sure! Here is the extracted skill you asked for:\n\n"
            f"{VALID_RESPONSE}\n\n"
            "Let me know if you need anything else!"
        )
        pipeline, calls = make_pipeline([wrapped])
        result = await pipeline._call_llm("test", [], [])
        assert result["name"] == VALID_SKILL["name"]
        assert calls["count"] == 1


# ── 5. Wrong schema (missing "steps") ─────────────────────────────────────

class TestSchemaValidation:
    def test_validator_rejects_missing_steps(self):
        with pytest.raises(SchemaValidationError, match="steps"):
            _validate_skill_schema({"name": "x", "description": "y"})

    def test_validator_rejects_non_list_steps(self):
        with pytest.raises(SchemaValidationError):
            _validate_skill_schema({"name": "x", "steps": "not a list"})

    @pytest.mark.asyncio
    async def test_missing_steps_retried_with_stricter_prompt(self, no_sleep, caplog):
        no_steps = json.dumps({"name": "x", "description": "y"})
        pipeline, calls = make_pipeline([no_steps, VALID_RESPONSE])
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            result = await pipeline._call_llm("test", [], [])
        assert result["name"] == VALID_SKILL["name"]
        assert calls["count"] == 2
        # first attempt: normal prompt; second attempt: stricter prompt
        assert STRICT_FORMAT_REMINDER not in calls["prompts"][0]
        assert STRICT_FORMAT_REMINDER in calls["prompts"][1]
        assert "Schema validation failed" in caplog.text

    @pytest.mark.asyncio
    async def test_persistent_bad_schema_exhausts_retries(self, no_sleep):
        no_steps = json.dumps({"name": "x"})
        pipeline, calls = make_pipeline([no_steps])
        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            await pipeline._call_llm("test", [], [])
        assert calls["count"] == 3


# ── 6. Timeout ────────────────────────────────────────────────────────────

class TestTimeout:
    @pytest.mark.asyncio
    async def test_slow_llm_raises_timeout_without_retry(self, no_sleep, monkeypatch, caplog):
        monkeypatch.setattr(skill_extractor, "LLM_TIMEOUT_SECONDS", 0.05)

        async def slow_response():
            await asyncio.sleep(5)
            return VALID_RESPONSE

        pipeline, calls = make_pipeline([slow_response])
        with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
            with pytest.raises(LLMTimeoutError):
                await pipeline._call_llm("test", [], [])
        assert calls["count"] == 1  # no retries — move on immediately
        assert "timed out" in caplog.text

    @pytest.mark.asyncio
    async def test_timeout_moves_to_next_cluster(self, no_sleep, monkeypatch, caplog):
        monkeypatch.setattr(skill_extractor, "LLM_TIMEOUT_SECONDS", 0.05)
        await seed_documents(["alpha", "beta"])

        async def slow_response():
            await asyncio.sleep(5)
            return VALID_RESPONSE

        pipeline, calls = make_pipeline([slow_response, VALID_RESPONSE])
        clusters = make_clusters(["alpha"], ["beta"])

        async with TestSessionLocal() as db:
            with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
                skills = await pipeline.extract_all_clusters(db, clusters)

        assert len(skills) == 1  # cluster 0 timed out, cluster 1 extracted
        assert await count_skills_in_db() == 1


# ── 7. 429 rate limit ─────────────────────────────────────────────────────

class TestRateLimit:
    @pytest.mark.asyncio
    async def test_backs_off_exponentially_then_succeeds(self, no_sleep, caplog):
        pipeline, calls = make_pipeline([
            FakeHTTPError(429, "429 Client Error: Too Many Requests"),
            FakeHTTPError(429, "429 Client Error: Too Many Requests"),
            VALID_RESPONSE,
        ])
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            result = await pipeline._call_llm("test", [], [])
        assert result["name"] == VALID_SKILL["name"]
        assert calls["count"] == 3
        assert "Rate limited" in caplog.text

        delays = [c.args[0] for c in no_sleep.await_args_list]
        assert len(delays) == 2
        assert delays[1] == 2 * delays[0]  # exponential backoff

    @pytest.mark.asyncio
    async def test_detected_from_message_without_response_attr(self, no_sleep):
        pipeline, calls = make_pipeline([
            Exception("Rate limit reached, too many requests"),
            VALID_RESPONSE,
        ])
        result = await pipeline._call_llm("test", [], [])
        assert calls["count"] == 2

    @pytest.mark.asyncio
    async def test_persistent_rate_limit_exhausts_retries(self, no_sleep):
        pipeline, calls = make_pipeline([FakeHTTPError(429, "429 Too Many Requests")])
        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            await pipeline._call_llm("test", [], [])
        assert calls["count"] == 3


# ── 8. 402 credits exhausted ──────────────────────────────────────────────

class TestCreditsExhausted:
    @pytest.mark.asyncio
    async def test_raises_immediately_without_retry(self, no_sleep, caplog):
        pipeline, calls = make_pipeline([
            FakeHTTPError(402, "402 Client Error: Payment Required"),
        ])
        with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
            with pytest.raises(LLMCreditsExhaustedError):
                await pipeline._call_llm("test", [], [])
        assert calls["count"] == 1       # no pointless retries
        no_sleep.assert_not_awaited()    # no backoff either
        assert "credits exhausted" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_detected_from_hf_credits_message(self, no_sleep):
        pipeline, calls = make_pipeline([
            Exception("You have exceeded your monthly included credits for Inference Providers."),
        ])
        with pytest.raises(LLMCreditsExhaustedError):
            await pipeline._call_llm("test", [], [])
        assert calls["count"] == 1

    @pytest.mark.asyncio
    async def test_stops_gracefully_saves_done_reports_remaining(self, no_sleep, caplog):
        """Cluster 0 succeeds, cluster 1 hits 402 → stop; cluster 2 untouched.

        The completed skill must survive (committed), and the log must name
        the clusters that were never extracted.
        """
        await seed_documents(["alpha", "beta", "gamma"])
        pipeline, calls = make_pipeline([
            VALID_RESPONSE,
            FakeHTTPError(402, "402 Client Error: Payment Required"),
        ])
        clusters = make_clusters(["alpha"], ["beta"], ["gamma"])

        async with TestSessionLocal() as db:
            with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
                skills = await pipeline.extract_all_clusters(db, clusters)

        assert len(skills) == 1
        assert calls["count"] == 2  # cluster 2 was never attempted
        # completed skill was committed, not rolled back
        assert await count_skills_in_db() == 1
        # remaining clusters are reported
        assert "credits exhausted" in caplog.text.lower()
        assert "cluster-1" in caplog.text
        assert "cluster-2" in caplog.text


# ── 9. 500 server error ───────────────────────────────────────────────────

class TestServerError:
    @pytest.mark.asyncio
    async def test_retried_three_times_with_backoff(self, no_sleep, caplog):
        pipeline, calls = make_pipeline([
            FakeHTTPError(500, "500 Server Error: Internal Server Error"),
            FakeHTTPError(500, "500 Server Error: Internal Server Error"),
            VALID_RESPONSE,
        ])
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            result = await pipeline._call_llm("test", [], [])
        assert result["name"] == VALID_SKILL["name"]
        assert calls["count"] == 3
        assert "LLM call error" in caplog.text

        delays = [c.args[0] for c in no_sleep.await_args_list]
        assert len(delays) == 2
        assert delays[1] > delays[0]  # backoff grows

    @pytest.mark.asyncio
    async def test_persistent_500_skips_cluster_keeps_others(self, no_sleep, caplog):
        await seed_documents(["alpha", "beta", "gamma"])
        # cluster 0: ok | cluster 1: three 500s | cluster 2: ok
        pipeline, calls = make_pipeline([
            VALID_RESPONSE,
            FakeHTTPError(500, "500 Server Error"),
            FakeHTTPError(500, "500 Server Error"),
            FakeHTTPError(500, "500 Server Error"),
            VALID_RESPONSE,
        ])
        clusters = make_clusters(["alpha"], ["beta"], ["gamma"])

        async with TestSessionLocal() as db:
            with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
                skills = await pipeline.extract_all_clusters(db, clusters)

        assert len(skills) == 2
        assert calls["count"] == 5
        assert "Failed to extract skill for cluster 'cluster-1'" in caplog.text
        assert await count_skills_in_db() == 2  # both good skills persisted


# ── 10. Zero / too few steps ──────────────────────────────────────────────

class TestMinimumSteps:
    def test_validator_rejects_zero_steps(self):
        with pytest.raises(SchemaValidationError, match="at least"):
            _validate_skill_schema({"name": "x", "steps": []})

    def test_validator_rejects_two_steps(self):
        two = dict(VALID_SKILL, steps=VALID_SKILL["steps"][:2])
        with pytest.raises(SchemaValidationError):
            _validate_skill_schema(two)

    def test_validator_accepts_three_steps(self):
        assert MIN_SKILL_STEPS == 3
        _validate_skill_schema(VALID_SKILL)  # must not raise

    @pytest.mark.asyncio
    async def test_zero_step_response_rejected_then_retried(self, no_sleep):
        empty_steps = json.dumps(dict(VALID_SKILL, steps=[]))
        pipeline, calls = make_pipeline([empty_steps, VALID_RESPONSE])
        result = await pipeline._call_llm("test", [], [])
        assert len(result["steps"]) == 3
        assert calls["count"] == 2

    @pytest.mark.asyncio
    async def test_persistent_zero_steps_skips_cluster(self, no_sleep, caplog):
        await seed_documents(["alpha"])
        empty_steps = json.dumps(dict(VALID_SKILL, steps=[]))
        pipeline, calls = make_pipeline([empty_steps])
        clusters = make_clusters(["alpha"])

        async with TestSessionLocal() as db:
            with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
                skills = await pipeline.extract_all_clusters(db, clusters)

        assert skills == []
        assert calls["count"] == 3
        assert await count_skills_in_db() == 0  # nothing bogus persisted
