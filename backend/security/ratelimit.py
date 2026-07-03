"""Per-API-key rate limiting with a sliding one-hour window.

In-process, like the existing ingestion task tracker — swap for a Redis
backend when running multiple workers. Only POST requests are counted so
that e.g. polling GET /api/ingest/status does not consume the ingestion
budget.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from backend.config import settings

_WINDOW_SECONDS = 3600.0


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int) -> None:
        """Record one event for ``key``; raise 429 when over ``limit``/hour."""
        now = time.monotonic()
        events = self._events[key]
        while events and now - events[0] > _WINDOW_SECONDS:
            events.popleft()
        if len(events) >= limit:
            retry_after = int(_WINDOW_SECONDS - (now - events[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({limit} requests/hour). Try later.",
                headers={"Retry-After": str(retry_after)},
            )
        events.append(now)

    def reset(self) -> None:
        """Clear all recorded events (used by tests)."""
        self._events.clear()


limiter = SlidingWindowLimiter()


def _caller_id(request: Request) -> str:
    """Identify the caller: API key if authenticated, else client IP."""
    api_key = getattr(request.state, "api_key", None)
    if api_key is not None:
        return f"key:{api_key.id}"
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


async def ingest_rate_limit(request: Request) -> None:
    if request.method != "POST":
        return
    limiter.check(
        f"ingest:{_caller_id(request)}", settings.RATE_LIMIT_INGEST_PER_HOUR
    )


async def query_rate_limit(request: Request) -> None:
    if request.method != "POST":
        return
    limiter.check(
        f"query:{_caller_id(request)}", settings.RATE_LIMIT_QUERY_PER_HOUR
    )
