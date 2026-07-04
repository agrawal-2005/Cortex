"""Ingestion API routes — Slack ZIP upload, Discord, file upload, status tracking."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session_factory, get_db
from backend.ingestion.confluence_json_ingester import ConfluenceJsonIngester
from backend.ingestion.discord_ingester import DiscordIngester
from backend.ingestion.file_upload_ingester import FileUploadIngester
from backend.ingestion.github_ingester import GitHubIngester
from backend.ingestion.github_json_ingester import GitHubJsonIngester
from backend.ingestion.jira_json_ingester import JiraJsonIngester
from backend.ingestion.slack_ingester import SlackExportIngester
from backend.models import Document
from backend.processing.embedder import DocumentEmbedder
from backend.processing.lazy_extraction import (
    ExtractionInProgressError,
    LazyExtractionService,
)
from backend.security.validation import redact_secrets, validate_upload
from backend.schemas import (
    DiscordLiveIngestRequest,
    DocumentCreate,
    GitHubIngestRequest,
    IngestStatusResponse,
)

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


async def _post_ingest_extraction(db: AsyncSession) -> dict[str, Any] | None:
    """Run lazy extraction after new documents were stored.

    Clusters everything (cheap) and pre-extracts only the top
    PRE_EXTRACT_TOP_N clusters; the rest become pending topics answered
    on demand at query time. Never fails the ingest request — extraction
    errors are logged and the summary is simply omitted.
    """
    try:
        return await LazyExtractionService().cluster_and_pre_extract(db)
    except ExtractionInProgressError:
        # Another ingest already triggered extraction — the new documents
        # stay unclustered until the next run or an on-demand query.
        logger.info("Post-ingest extraction skipped: run already in progress")
        return None
    except Exception as exc:  # noqa: BLE001 — ingest must survive this
        logger.error(
            "Post-ingest lazy extraction failed: %s", redact_secrets(str(exc))
        )
        return None


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
    content = await file.read()
    validate_upload(file.filename or "", len(content), {".zip"})

    task_id = str(uuid.uuid4())
    _set_task(task_id, status="running", progress={"stage": "extracting"})

    tmpdir = tempfile.mkdtemp(prefix="cortex_slack_")

    try:
        # Write uploaded zip to disk
        zip_path = f"{tmpdir}/export.zip"
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

        _set_task(task_id, status="running", progress={**stats, "stage": "extracting"})
        extraction = await _post_ingest_extraction(db)

        _set_task(task_id, status="completed", progress={**stats, "extraction": extraction})
        logger.info("Slack ingestion task %s completed: %s", task_id, stats)

    except Exception as exc:
        safe_error = redact_secrets(str(exc))
        logger.error("Slack ingestion task %s failed: %s", task_id, safe_error)
        _set_task(task_id, status="failed", error=safe_error)
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
    raw = await file.read()
    validate_upload(filename, len(raw), {".csv", ".json"})

    try:
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

    if result.get("documents_created"):
        result["extraction"] = await _post_ingest_extraction(db)

    return result


# ── POST /github — GitHub repository ingestion ────────────────────────────


async def _run_github_ingest(task_id: str, payload: GitHubIngestRequest) -> None:
    """Background worker: fetch from GitHub, store documents, track progress."""
    ingester = GitHubIngester(
        repo=payload.repo,
        token=payload.token,
        months=payload.months,
        max_requests=payload.max_requests,
        include_comments=payload.include_comments,
    )
    try:
        docs = await ingester.ingest()
        _set_task(
            task_id,
            status="running",
            progress={"stage": "storing", "documents_fetched": len(docs)},
        )
        async with async_session_factory() as db:
            ingested = await _store_documents(docs, db)
            await db.commit()
            extraction = None
            if ingested:
                _set_task(
                    task_id,
                    status="running",
                    progress={
                        "stage": "extracting",
                        "documents_ingested": ingested,
                    },
                )
                extraction = await _post_ingest_extraction(db)
        _set_task(
            task_id,
            status="completed",
            progress={
                "documents_ingested": ingested,
                "stats": ingester.stats,
                "extraction": extraction,
            },
        )
        logger.info(
            "GitHub ingestion task %s completed: %d docs stored (%s)",
            task_id, ingested, ingester.stats,
        )
    except Exception as exc:
        safe_error = redact_secrets(str(exc))
        logger.error("GitHub ingestion task %s failed: %s", task_id, safe_error)
        _set_task(task_id, status="failed", error=safe_error)


@router.post(
    "/github",
    response_model=IngestStatusResponse,
    status_code=202,
    summary="Ingest a GitHub repository (background task)",
    description=(
        "Pulls issues, PRs, discussions, and docs from a public GitHub "
        "repo (owner/repo) via the REST API and stores them as Documents. "
        "Runs in the background — poll GET /status?task_id=... for progress. "
        "An optional token (or GITHUB_TOKEN env var) raises the rate limit."
    ),
)
async def ingest_github_repo(payload: GitHubIngestRequest) -> IngestStatusResponse:
    # repo format is validated by the GitHubIngestRequest schema (owner/repo).
    task_id = str(uuid.uuid4())
    _set_task(task_id, status="running", progress={"stage": "fetching"})
    asyncio.create_task(_run_github_ingest(task_id, payload))
    return IngestStatusResponse(**_tasks[task_id])


# ── POST /discord/* — Discord ingestion ──────────────────────────────────


async def _store_documents(
    docs: list[DocumentCreate], db: AsyncSession
) -> int:
    """Store documents and embed them, skipping ones already ingested (same
    source_type + source_id) so that re-syncing a source doesn't create
    duplicates."""
    if not docs:
        return 0
    source_ids = {d.source_id for d in docs if d.source_id}
    existing: set[tuple[str, str]] = set()
    if source_ids:
        result = await db.execute(
            select(Document.source_type, Document.source_id).where(
                Document.source_id.in_(source_ids)
            )
        )
        existing = {tuple(row) for row in result.all()}
    new_docs: list[Document] = []
    for payload in docs:
        if payload.source_id and (payload.source_type, payload.source_id) in existing:
            continue
        doc = Document(**payload.model_dump())
        db.add(doc)
        new_docs.append(doc)
    if new_docs:
        await db.flush()
        await DocumentEmbedder().embed_documents(
            db, document_ids=[d.id for d in new_docs]
        )
    return len(new_docs)


@router.post(
    "/discord/upload",
    summary="Upload a DiscordChatExporter JSON export",
    description=(
        "Accepts a `.json` file produced by DiscordChatExporter "
        "(an object with `guild`, `channel`, and `messages` keys) and "
        "ingests each message as a Document with `source_type='discord'`."
    ),
)
async def ingest_discord_export(
    file: UploadFile = File(..., description="DiscordChatExporter .json file"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    raw = await file.read()
    validate_upload(file.filename or "", len(raw), {".json"})

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {exc}")

    ingester = DiscordIngester(download_attachments=False)
    try:
        docs = await ingester.parse_export(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ingested = await _store_documents(docs, db)
    extraction = await _post_ingest_extraction(db) if ingested else None
    return {
        "status": "success",
        "documents_ingested": ingested,
        "stats": ingester.stats,
        "extraction": extraction,
    }


@router.post(
    "/discord/live",
    summary="Ingest Discord channels via bot token",
    description=(
        "Connects to the Discord REST API with a bot token (from the "
        "request body or the DISCORD_BOT_TOKEN env var) and ingests "
        "messages from the given channels, including threads."
    ),
)
async def ingest_discord_live(
    payload: DiscordLiveIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    ingester = DiscordIngester(
        bot_token=payload.bot_token,
        guild_id=payload.guild_id,
        channel_ids=payload.channel_ids,
        max_messages_per_channel=payload.max_messages_per_channel,
    )
    if not ingester.bot_token:
        raise HTTPException(
            status_code=400,
            detail="No Discord bot token: provide bot_token or set DISCORD_BOT_TOKEN.",
        )

    try:
        docs = await ingester.ingest()
    except ConnectionError as exc:
        raise HTTPException(status_code=502, detail=redact_secrets(str(exc)))
    except Exception as exc:
        safe_error = redact_secrets(str(exc))
        logger.error("Discord live ingestion failed: %s", safe_error)
        raise HTTPException(
            status_code=502, detail=f"Discord ingestion failed: {safe_error}"
        )

    ingested = await _store_documents(docs, db)
    extraction = await _post_ingest_extraction(db) if ingested else None
    return {
        "status": "success",
        "documents_ingested": ingested,
        "stats": ingester.stats,
        "extraction": extraction,
    }


# ── POST /jira — Jira JSON export ─────────────────────────────────────────


@router.post(
    "/jira",
    summary="Upload a Jira JSON export",
    description=(
        "Accepts a `.json` file with an `issues` array (key, summary, "
        "description, comments, ...) and ingests each issue as a Document "
        "with `source_type='jira'`. Content includes the summary, "
        "description, and all comments with authors and timestamps."
    ),
)
async def ingest_jira_export(
    file: UploadFile = File(..., description="Jira export .json file"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    raw = await file.read()
    validate_upload(file.filename or "", len(raw), {".json"})

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {exc}")

    ingester = JiraJsonIngester()
    try:
        docs = await ingester.parse_export(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ingested = await _store_documents(docs, db)
    extraction = await _post_ingest_extraction(db) if ingested else None
    return {
        "status": "success",
        "documents_ingested": ingested,
        "stats": ingester.stats,
        "extraction": extraction,
    }


# ── POST /confluence — Confluence JSON export ─────────────────────────────


@router.post(
    "/confluence",
    summary="Upload a Confluence JSON export",
    description=(
        "Accepts a `.json` file with a `pages` array (id, title, space, "
        "body, author, created, last_modified, url) and ingests each page "
        "as a Document with `source_type='confluence'`. Uses "
        "`last_modified` as the document timestamp for recency-based "
        "conflict resolution."
    ),
)
async def ingest_confluence_export(
    file: UploadFile = File(..., description="Confluence export .json file"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    raw = await file.read()
    validate_upload(file.filename or "", len(raw), {".json"})

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {exc}")

    ingester = ConfluenceJsonIngester()
    try:
        docs = await ingester.parse_export(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ingested = await _store_documents(docs, db)
    extraction = await _post_ingest_extraction(db) if ingested else None
    return {
        "status": "success",
        "documents_ingested": ingested,
        "stats": ingester.stats,
        "extraction": extraction,
    }


# ── POST /github/upload — GitHub JSON export ──────────────────────────────


@router.post(
    "/github/upload",
    summary="Upload a GitHub JSON export",
    description=(
        "Accepts a `.json` file with an `items` array of PRs and issues "
        "in GitHub REST API shape (number, title, body, state, "
        "user.login, labels, comments; PRs carry a `pull_request` key) "
        "and ingests each item as a Document with "
        "`source_type='github_pr'` or `'github_issue'`. No GitHub API "
        "calls are made — the file is the source of truth."
    ),
)
async def ingest_github_export(
    file: UploadFile = File(..., description="GitHub export .json file"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    raw = await file.read()
    validate_upload(file.filename or "", len(raw), {".json"})

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {exc}")

    ingester = GitHubJsonIngester()
    try:
        docs = await ingester.parse_export(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ingested = await _store_documents(docs, db)
    extraction = await _post_ingest_extraction(db) if ingested else None
    return {
        "status": "success",
        "documents_ingested": ingested,
        "stats": ingester.stats,
        "extraction": extraction,
    }


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
