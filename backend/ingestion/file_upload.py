"""File-based ingestion endpoints for Slack exports and generic CSV/JSON uploads."""

import csv
import io
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Document

logger = logging.getLogger(__name__)

router = APIRouter()

# Slack message subtypes to skip
_SKIP_SUBTYPES = {"channel_join", "channel_leave"}


def _parse_slack_messages(data: Any) -> list[dict[str, Any]]:
    """Extract messages from either a flat array or a dict with a 'messages' key."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "messages" in data:
        return data["messages"]
    raise ValueError(
        "Unsupported Slack export format: expected a JSON array of messages "
        "or an object with a 'messages' key."
    )


@router.post("/slack-export")
async def ingest_slack_export(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a Slack export JSON file and ingest messages as documents.

    Accepts a ``.json`` file containing either:
    - A JSON array of Slack message objects, or
    - A JSON object with a ``messages`` key holding the array.

    Each message with non-empty text (and not a join/leave event) is stored as
    a Document with ``source_type='slack'``.
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=400,
            detail="Only .json files are accepted for Slack export ingestion.",
        )

    try:
        raw = await file.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON file: {exc}",
        )

    try:
        messages = _parse_slack_messages(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ingested = 0
    skipped = 0

    for msg in messages:
        # Skip non-message types and join/leave subtypes
        if msg.get("subtype") in _SKIP_SUBTYPES:
            skipped += 1
            continue

        text = (msg.get("text") or "").strip()
        if not text:
            skipped += 1
            continue

        ts = msg.get("ts", "")
        user = msg.get("user", "unknown")
        channel = msg.get("channel", "unknown")

        doc = Document(
            content=text,
            source_type="slack",
            source_id=ts,
            channel_or_project=channel,
            author_name=user,
        )
        db.add(doc)
        ingested += 1

    if ingested:
        await db.flush()

    return {
        "status": "success",
        "documents_ingested": ingested,
        "skipped": skipped,
    }


@router.post("/upload")
async def ingest_file_upload(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a CSV or JSON file and ingest rows/objects as documents.

    - **JSON** files must contain an array of objects, each with at least
      a ``content`` key.
    - **CSV** files must have a header row with at least a ``content`` column.

    Additional recognised columns/keys: ``source_id``, ``source_link``,
    ``source_label``, ``channel_or_project``, ``author_name``, ``author_role``.
    """
    filename = file.filename or ""
    if not (filename.endswith(".json") or filename.endswith(".csv")):
        raise HTTPException(
            status_code=400,
            detail="Only .json and .csv files are accepted.",
        )

    try:
        raw = await file.read()
        content_str = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to decode file as UTF-8: {exc}",
        )

    errors: list[str] = []
    rows: list[dict[str, Any]] = []

    if filename.endswith(".json"):
        try:
            data = json.loads(content_str)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON file: {exc}",
            )
        if not isinstance(data, list):
            raise HTTPException(
                status_code=400,
                detail="JSON file must contain an array of objects.",
            )
        rows = data
    else:
        # CSV
        reader = csv.DictReader(io.StringIO(content_str))
        rows = list(reader)

    ingested = 0
    skipped = 0

    for idx, row in enumerate(rows):
        body = (row.get("content") or "").strip()

        if not body:
            errors.append(
                f"Row {idx + 1}: missing required 'content' field."
            )
            skipped += 1
            continue

        # Optional fields
        source_id = (row.get("source_id") or "").strip() or f"{source_type}-{idx}"
        source_link = (row.get("source_link") or "").strip() or None
        source_label = (row.get("source_label") or "").strip() or None
        channel_or_project = (row.get("channel_or_project") or "").strip() or None
        author_name = (row.get("author_name") or "").strip() or None
        author_role = (row.get("author_role") or "").strip() or None

        doc = Document(
            content=body,
            source_type=source_type,
            source_id=source_id,
            source_link=source_link,
            source_label=source_label,
            channel_or_project=channel_or_project,
            author_name=author_name,
            author_role=author_role,
        )
        db.add(doc)
        ingested += 1

    if ingested:
        await db.flush()

    return {
        "status": "success",
        "documents_ingested": ingested,
        "skipped": skipped,
        "errors": errors,
    }
