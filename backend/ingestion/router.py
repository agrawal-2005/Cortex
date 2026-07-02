from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Document
from backend.schemas import DocumentCreate, DocumentResponse

router = APIRouter()


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def create_document(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Ingest a single document and optionally trigger background processing."""
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

    # TODO: trigger Celery processing task
    # from backend.tasks.process import process_document
    # process_document.delay(doc.id)

    return DocumentResponse.model_validate(doc)


@router.post("/batch", response_model=list[DocumentResponse], status_code=201)
async def create_documents_batch(
    payloads: list[DocumentCreate],
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """Ingest a batch of documents."""
    results: list[DocumentResponse] = []

    for payload in payloads:
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

        results.append(DocumentResponse.model_validate(doc))

    # TODO: trigger Celery processing tasks for all documents
    # from backend.tasks.process import process_document
    # for r in results:
    #     process_document.delay(r.id)

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
