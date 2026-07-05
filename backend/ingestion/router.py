from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Document
from backend.schemas import DocumentCreate, DocumentResponse

router = APIRouter()


async def _find_existing(
    db: AsyncSession, source_type: str, source_id: str
) -> Document | None:
    """Return the already-ingested document for (source_type, source_id),
    if any — used to keep document ingestion idempotent."""
    result = await db.execute(
        select(Document)
        .where(
            Document.source_type == source_type,
            Document.source_id == source_id,
        )
        .limit(1)
    )
    return result.scalars().first()


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def create_document(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Ingest a single document (idempotent: re-posting the same
    source_type + source_id returns the existing document instead of
    creating a duplicate)."""
    existing = await _find_existing(db, payload.source_type, payload.source_id)
    if existing is not None:
        return DocumentResponse.model_validate(existing)

    doc = Document(
        content=payload.content,
        source_type=payload.source_type,
        source_id=payload.source_id,
        source_link=payload.source_link,
        source_label=payload.source_label,
        channel_or_project=payload.channel_or_project,
        author_name=payload.author_name,
        author_role=payload.author_role,
        created_at=payload.created_at,
        embedding_id=payload.embedding_id,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    return DocumentResponse.model_validate(doc)


@router.post("/batch", response_model=list[DocumentResponse], status_code=201)
async def create_documents_batch(
    payloads: list[DocumentCreate],
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """Ingest a batch of documents. Duplicates (same source_type +
    source_id, whether already in the database or repeated within the
    batch) are not re-created; the existing document is returned in
    their place, so the response stays 1:1 with the request."""
    results: list[DocumentResponse] = []
    seen_in_batch: dict[tuple[str, str], Document] = {}

    for payload in payloads:
        key = (payload.source_type, payload.source_id)
        existing = seen_in_batch.get(key) or await _find_existing(
            db, payload.source_type, payload.source_id
        )
        if existing is not None:
            results.append(DocumentResponse.model_validate(existing))
            continue

        doc = Document(
            content=payload.content,
            source_type=payload.source_type,
            source_id=payload.source_id,
            source_link=payload.source_link,
            source_label=payload.source_label,
            channel_or_project=payload.channel_or_project,
            author_name=payload.author_name,
            author_role=payload.author_role,
            created_at=payload.created_at,
            embedding_id=payload.embedding_id,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        seen_in_batch[key] = doc

        results.append(DocumentResponse.model_validate(doc))

    return results


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List documents with pagination."""
    result = await db.execute(
        select(Document).offset(skip).limit(limit).order_by(Document.ingested_at.desc())
    )
    rows = result.scalars().all()
    return [DocumentResponse.model_validate(row) for row in rows]


@router.get("/documents/source-types", response_model=list[str])
async def list_source_types(
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """List the distinct source_types of all ingested documents.

    Used by the UI to show which integrations are connected without
    paginating through every document.
    """
    result = await db.execute(select(Document.source_type).distinct())
    return [row for row in result.scalars().all() if row]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retrieve a single document by ID."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.model_validate(doc)
