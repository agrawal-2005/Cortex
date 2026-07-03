"""Connected-source management — tokens are Fernet-encrypted at rest and
never returned by any endpoint after creation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.knowledge.models import ConnectedSource
from backend.security.crypto import encrypt_token

router = APIRouter(tags=["sources"])


class ConnectedSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_type: str = Field(pattern=r"^(github|discord|slack)$")
    token: str | None = None
    config: dict = Field(default_factory=dict)


class ConnectedSourceResponse(BaseModel):
    """Public view of a connected source — deliberately has NO token field."""

    id: str
    name: str
    source_type: str
    has_token: bool
    config: dict

    model_config = {"from_attributes": True}


def _to_response(source: ConnectedSource) -> ConnectedSourceResponse:
    return ConnectedSourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        has_token=source.encrypted_token is not None,
        config=source.config or {},
    )


@router.post("/", response_model=ConnectedSourceResponse, status_code=201)
async def create_source(
    body: ConnectedSourceCreate,
    db: AsyncSession = Depends(get_db),
) -> ConnectedSourceResponse:
    source = ConnectedSource(
        name=body.name,
        source_type=body.source_type,
        encrypted_token=encrypt_token(body.token) if body.token else None,
        config=body.config,
    )
    db.add(source)
    await db.flush()
    return _to_response(source)


@router.get("/", response_model=list[ConnectedSourceResponse])
async def list_sources(
    db: AsyncSession = Depends(get_db),
) -> list[ConnectedSourceResponse]:
    result = await db.execute(
        select(ConnectedSource).order_by(ConnectedSource.created_at.desc())
    )
    return [_to_response(s) for s in result.scalars().all()]


@router.get("/{source_id}", response_model=ConnectedSourceResponse)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConnectedSourceResponse:
    source = await db.get(ConnectedSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return _to_response(source)


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    source = await db.get(ConnectedSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
