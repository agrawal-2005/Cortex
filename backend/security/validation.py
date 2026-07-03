"""Input validation and secret-hygiene helpers."""

from __future__ import annotations

import re

from fastapi import HTTPException

from backend.config import settings

# Global whitelist of upload extensions; endpoints may restrict further.
ALLOWED_UPLOAD_EXTENSIONS = {".zip", ".json", ".csv", ".pdf"}

# GitHub owner/repo: alphanumerics, hyphens, underscores, dots — one slash.
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")

# Secret-looking substrings that must never reach logs or API responses.
_SECRET_PATTERNS = re.compile(
    r"(ghp_[A-Za-z0-9]{4,}"          # GitHub classic PAT
    r"|github_pat_[A-Za-z0-9_]{4,}"  # GitHub fine-grained PAT
    r"|gho_[A-Za-z0-9]{4,}"          # GitHub OAuth token
    r"|xox[baprs]-[A-Za-z0-9-]{4,}"  # Slack tokens
    r"|hf_[A-Za-z0-9]{4,}"           # HuggingFace tokens
    r"|Bearer\s+\S+"                 # any bearer credential
    r"|Bot\s+[A-Za-z0-9_.-]{20,})"   # Discord bot tokens
)


def max_upload_bytes() -> int:
    return settings.MAX_UPLOAD_MB * 1024 * 1024


def validate_upload(filename: str, size: int, allowed: set[str]) -> None:
    """Reject uploads with disallowed extensions or exceeding the size cap.

    Raises:
        HTTPException: 400 for a bad extension, 413 for an oversized file.
    """
    lowered = (filename or "").lower()
    ext = "." + lowered.rsplit(".", 1)[-1] if "." in lowered else ""
    if ext not in allowed or ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(sorted(allowed))} files are accepted.",
        )
    if size > max_upload_bytes():
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_UPLOAD_MB}MB upload limit.",
        )


def validate_repo(repo: str) -> str:
    """Validate 'owner/repo' format; returns the value for pydantic use."""
    if not REPO_PATTERN.match(repo or ""):
        raise ValueError("repo must be in 'owner/repo' format")
    return repo


def redact_secrets(text: str) -> str:
    """Mask token-like substrings before a string is logged or returned."""
    return _SECRET_PATTERNS.sub("[REDACTED]", text)
