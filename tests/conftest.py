from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from backend.database import Base, get_db
from backend.main import app
from backend.processing.embedder import DocumentEmbedder
from backend.processing.embeddings import EmbeddingService
from backend.vectorstore.store import VectorStore

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine_test, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def _offline_embeddings(monkeypatch):
    """Keep unit tests fully offline and isolated.

    - EmbeddingService would otherwise load the real sentence-transformers
      model (HTTP call to the HuggingFace hub on load) — return fake
      vectors instead.
    - DocumentEmbedder / VectorStore would otherwise write to and read
      from the real local ChromaDB store (./chroma_data), polluting dev
      data and making assertions depend on local state.
    """
    monkeypatch.setattr(
        EmbeddingService, "generate_embedding", lambda self, text: [0.1] * 384
    )
    monkeypatch.setattr(
        EmbeddingService,
        "generate_embeddings",
        lambda self, texts: [[0.1] * 384 for _ in texts],
    )
    monkeypatch.setattr(
        DocumentEmbedder,
        "embed_documents",
        AsyncMock(
            return_value={"embedded": 0, "skipped": 0, "errors": 0, "total": 0}
        ),
    )
    monkeypatch.setattr(VectorStore, "search", lambda self, *a, **kw: [])


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
