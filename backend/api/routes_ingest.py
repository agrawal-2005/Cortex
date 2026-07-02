"""Ingestion API routes — Slack ZIP upload, file upload, status tracking."""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.ingestion.file_upload_ingester import FileUploadIngester
from backend.ingestion.slack_ingester import SlackExportIngester
from backend.schemas import IngestStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])

# Simple in-memory task tracker (swap for Redis/Celery in production)
_tasks: dict[str, dict[str, Any]] = {}


def _set_task(task_id: str, **kwargs: Any) -> None:
    _tasks[task_id] = {
        "task_id": task_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }


# ── POST /slack — Upload Slack export ZIP ─────────────────────────────────


@router.post(
    "/slack",
    response_model=IngestStatusResponse,
    status_code=202,
    summary="Upload a Slack export ZIP file",
    description=(
        "Accepts a `.zip` Slack export archive. Extracts it, parses "
        "all channels/messages/threads, stores Documents in PostgreSQL, "
        "and generates embeddings in ChromaDB."
    ),
)
async def ingest_slack_export(
    file: UploadFile = File(..., description="Slack export .zip file"),
    db: AsyncSession = Depends(get_db),
) -> IngestStatusResponse:
    filename = file.filename or ""
    if not filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only .zip files are accepted for Slack export ingestion.",
        )

    task_id = str(uuid.uuid4())
    _set_task(task_id, status="running", progress={"stage": "extracting"})

    tmpdir = tempfile.mkdtemp(prefix="cortex_slack_")

    try:
        # Write uploaded zip to disk
        zip_path = f"{tmpdir}/export.zip"
        content = await file.read()
        with open(zip_path, "wb") as f:
            f.write(content)

        # Extract
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmpdir)

        _set_task(task_id, status="running", progress={"stage": "parsing"})

        # Find the export root (might be nested one level)
        import os
        export_root = tmpdir
        entries = [e for e in os.listdir(tmpdir) if not e.startswith(".") and e != "export.zip"]
        if len(entries) == 1 and os.path.isdir(os.path.join(tmpdir, entries[0])):
            export_root = os.path.join(tmpdir, entries[0])

        # Run ingestion
        ingester = SlackExportIngester(export_root)
        _set_task(task_id, status="running", progress={"stage": "ingesting"})
        stats = await ingester.ingest(db)

        _set_task(task_id, status="completed", progress=stats)
        logger.info("Slack ingestion task %s completed: %s", task_id, stats)

    except Exception as exc:
        logger.error("Slack ingestion task %s failed: %s", task_id, exc)
        _set_task(task_id, status="failed", error=str(exc))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return IngestStatusResponse(**_tasks[task_id])


# ── POST /file — Upload CSV/JSON file ────────────────────────────────────


@router.post(
    "/file",
    summary="Upload a CSV or JSON file",
    description=(
        "Accepts a `.csv` or `.json` file with document records. "
        "Each record must have a `content` field. Optional fields: "
        "source_id, source_link, source_label, channel_or_project, "
        "author_name, author_role."
    ),
)
async def ingest_file(
    file: UploadFile = File(..., description=".csv or .json file"),
    source_type: str = Form(..., description="e.g. jira, notion, custom"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    filename = file.filename or ""
    if not (filename.endswith(".json") or filename.endswith(".csv")):
        raise HTTPException(
            status_code=400,
            detail="Only .csv and .json files are accepted.",
        )

    try:
        raw = await file.read()
        content_str = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Cannot decode file: {exc}")

    ingester = FileUploadIngester()

    if filename.endswith(".json"):
        result = await ingester.ingest_json(content_str, source_type, db)
    else:
        result = await ingester.ingest_csv(content_str, source_type, db)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("detail", "Unknown error"))

    return result


# ── GET /status — Check ingestion progress ────────────────────────────────


@router.get(
    "/status",
    response_model=IngestStatusResponse,
    summary="Check ingestion task status",
)
async def get_ingest_status(
    task_id: str,
) -> IngestStatusResponse:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return IngestStatusResponse(**_tasks[task_id])
