"""Security controls: API key auth, input validation, rate limiting,
token encryption, and CORS configuration."""

import io
import uuid

import pytest

from backend.config import Settings, settings
from backend.knowledge.models import ApiKey
from backend.security.auth import generate_api_key, hash_api_key
from backend.security.crypto import decrypt_token, encrypt_token
from backend.security.validation import redact_secrets, validate_repo
from tests.conftest import TestSessionLocal


# ── API key authentication ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(anon_client):
    for path in ("/api/skills/", "/api/v1/skills/", "/api/sources/"):
        res = await anon_client.get(path)
        assert res.status_code == 401, path
    res = await anon_client.post("/api/query/", json={"question": "hi"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401(anon_client):
    res = await anon_client.get(
        "/api/skills/", headers={"X-API-Key": "ctx_not-a-real-key"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_revoked_api_key_returns_401(anon_client):
    key = generate_api_key()
    async with TestSessionLocal() as db:
        db.add(
            ApiKey(
                name="revoked",
                key_hash=hash_api_key(key),
                prefix=key[:8],
                is_active=False,
            )
        )
        await db.commit()
    res = await anon_client.get("/api/skills/", headers={"X-API-Key": key})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_valid_api_key_grants_access(client):
    res = await client.get("/api/skills/")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_health_is_public(anon_client):
    res = await anon_client.get("/health")
    assert res.status_code == 200


def test_api_keys_stored_hashed_only():
    key = generate_api_key()
    assert key.startswith("ctx_")
    hashed = hash_api_key(key)
    assert hashed != key
    assert len(hashed) == 64  # sha256 hex


# ── Input validation ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_rejects_disallowed_extension(client):
    files = {"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
    res = await client.post(
        "/api/ingest/file", files=files, data={"source_type": "custom"}
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    big = b"x" * (1024 * 1024 + 1)
    files = {"file": ("big.csv", io.BytesIO(big), "text/csv")}
    res = await client.post(
        "/api/ingest/file", files=files, data={"source_type": "custom"}
    )
    assert res.status_code == 413


@pytest.mark.asyncio
async def test_github_repo_format_validated(client):
    for bad in ("no-slash", "a/b/c", "own er/repo", "../etc/passwd", ""):
        res = await client.post("/api/ingest/github", json={"repo": bad})
        assert res.status_code == 422, bad


def test_validate_repo_accepts_normal_repos():
    assert validate_repo("usestrix/strix") == "usestrix/strix"
    assert validate_repo("agrawal-2005/Cortex.js") == "agrawal-2005/Cortex.js"


def test_redact_secrets_masks_tokens():
    text = (
        "failed with ghp_abcDEF123456 and xoxb-1234-abcd "
        "and Bearer sk-secret and github_pat_11AAAA_bbb"
    )
    redacted = redact_secrets(text)
    assert "ghp_" not in redacted
    assert "xoxb-" not in redacted
    assert "sk-secret" not in redacted
    assert "github_pat_" not in redacted
    assert "[REDACTED]" in redacted


@pytest.mark.asyncio
async def test_ingest_error_never_echoes_token(client, monkeypatch):
    """A failing GitHub ingestion must not leak the token via task status."""
    from backend.ingestion.github_ingester import GitHubIngester

    token = "ghp_supersecret1234567890"

    async def boom(self):
        raise RuntimeError(f"401 bad credentials for token {token}")

    monkeypatch.setattr(GitHubIngester, "ingest", boom)

    res = await client.post(
        "/api/ingest/github", json={"repo": "owner/repo", "token": token}
    )
    assert res.status_code == 202
    task_id = res.json()["task_id"]

    # background task runs on the same loop; poll status until it settles
    import asyncio

    for _ in range(50):
        status = (
            await client.get("/api/ingest/status", params={"task_id": task_id})
        ).json()
        if status["status"] == "failed":
            break
        await asyncio.sleep(0.01)

    assert status["status"] == "failed"
    assert token not in (status.get("error") or "")
    assert "[REDACTED]" in status["error"]


# ── Rate limiting ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ingest_rate_limit_returns_429(client, monkeypatch):
    from backend.ingestion.github_ingester import GitHubIngester

    async def fake_ingest(self):
        return []

    monkeypatch.setattr(GitHubIngester, "ingest", fake_ingest)
    monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_HOUR", 2)
    payload = {"repo": "owner/repo"}
    codes = []
    for _ in range(3):
        res = await client.post("/api/ingest/github", json=payload)
        codes.append(res.status_code)
    assert codes[0] == 202 and codes[1] == 202
    assert codes[2] == 429
    assert "Retry-After" in res.headers


@pytest.mark.asyncio
async def test_query_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_QUERY_PER_HOUR", 2)
    codes = []
    for _ in range(3):
        res = await client.post("/api/query/", json={"question": "how?"})
        codes.append(res.status_code)
    assert codes == [200, 200, 429]


@pytest.mark.asyncio
async def test_status_polling_not_rate_limited(client, monkeypatch):
    """GET /status must not consume the ingestion budget."""
    monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_HOUR", 1)
    for _ in range(5):
        res = await client.get(
            "/api/ingest/status", params={"task_id": str(uuid.uuid4())}
        )
        assert res.status_code == 404  # unknown task, but never 429


# ── Token encryption ──────────────────────────────────────────────────────


def test_fernet_round_trip():
    secret = "ghp_verysecrettoken12345"
    ciphertext = encrypt_token(secret)
    assert secret not in ciphertext
    assert decrypt_token(ciphertext) == secret


@pytest.mark.asyncio
async def test_connected_source_token_encrypted_and_never_returned(client):
    secret = "xoxb-1111-2222-secret"
    res = await client.post(
        "/api/sources/",
        json={"name": "team slack", "source_type": "slack", "token": secret},
    )
    assert res.status_code == 201
    body = res.json()
    assert "token" not in body
    assert body["has_token"] is True
    source_id = body["id"]

    # Not in GET responses either
    for resp in (
        await client.get("/api/sources/"),
        await client.get(f"/api/sources/{source_id}"),
    ):
        assert secret not in resp.text
        assert "encrypted_token" not in resp.text

    # Stored ciphertext, not plaintext
    from backend.knowledge.models import ConnectedSource

    async with TestSessionLocal() as db:
        source = await db.get(ConnectedSource, source_id)
        assert source.encrypted_token != secret
        assert secret not in source.encrypted_token
        assert decrypt_token(source.encrypted_token) == secret


# ── CORS configuration ────────────────────────────────────────────────────


def test_cors_dev_defaults_to_localhost_only():
    s = Settings(ENVIRONMENT="development", CORS_ORIGINS="")
    origins = s.cors_origins_list()
    assert "*" not in origins
    assert all("localhost" in o or "127.0.0.1" in o for o in origins)


def test_cors_production_requires_explicit_origins():
    s = Settings(ENVIRONMENT="production", CORS_ORIGINS="")
    with pytest.raises(RuntimeError):
        s.cors_origins_list()


def test_cors_production_uses_configured_domain():
    s = Settings(
        ENVIRONMENT="production", CORS_ORIGINS="https://cortex.example.com"
    )
    assert s.cors_origins_list() == ["https://cortex.example.com"]


def test_app_cors_not_wildcard():
    from fastapi.middleware.cors import CORSMiddleware

    from backend.main import app

    cors = next(
        m for m in app.user_middleware if m.cls is CORSMiddleware
    )
    assert cors.kwargs["allow_origins"] != ["*"]
