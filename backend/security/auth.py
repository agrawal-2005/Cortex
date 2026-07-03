"""API key authentication.

Keys look like ``ctx_<random>`` and are shown to the caller exactly once
at creation time. Only a SHA-256 hash is stored, so a database leak does
not leak usable credentials.

All routes except the exempt ones (health check, docs) require a valid
key in the ``X-API-Key`` header; requests without one get a 401.
"""

from __future__ import annotations

import hashlib
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.knowledge.models import ApiKey

API_KEY_HEADER = "X-API-Key"
_KEY_PREFIX = "ctx_"


def generate_api_key() -> str:
    """Generate a new plaintext API key (only ever shown once)."""
    return _KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """Deterministic hash for storage and lookup."""
    return hashlib.sha256(key.encode()).hexdigest()


async def require_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """FastAPI dependency: reject requests without a valid X-API-Key.

    On success, stores the ApiKey row on ``request.state.api_key`` so
    downstream dependencies (e.g. the rate limiter) can identify the caller.
    """
    provided = request.headers.get(API_KEY_HEADER)
    if not provided:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == hash_api_key(provided))
    )
    api_key = result.scalar_one_or_none()
    if api_key is None or not api_key.is_active:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    request.state.api_key = api_key
    return api_key
