from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from backend.database import Base, get_db
from backend.knowledge.models import ApiKey
from backend.main import app
from backend.processing.embedder import DocumentEmbedder
from backend.processing.embeddings import EmbeddingService
from backend.security.auth import generate_api_key, hash_api_key
from backend.security.ratelimit import limiter
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


@pytest.fixture(autouse=True)
def _stub_post_ingest_extraction(monkeypatch):
    """Ingestion routes trigger lazy extraction automatically.

    Running it for real in every upload test would build HDBSCAN clusters
    and a Groq client. Stub it; wiring tests assert the stub was awaited,
    and tests/test_lazy_extraction.py exercises the real service directly.
    """
    from backend.processing.lazy_extraction import LazyExtractionService

    mock = AsyncMock(
        return_value={
            "documents": 0,
            "clusters": 0,
            "skills_extracted": 0,
            "already_covered": 0,
            "pending_topics": 0,
        }
    )
    monkeypatch.setattr(LazyExtractionService, "cluster_and_pre_extract", mock)
    return mock


@pytest.fixture(autouse=True)
def _stub_on_demand_extraction(monkeypatch):
    """Query-route tests must never reach a real LLM.

    The query route triggers on-demand extraction when documents match no
    skill — stub it to "nothing extracted" so legacy query tests keep
    exercising the fallback paths offline. tests/test_lazy_extraction.py
    restores the real method and mocks the LLM chain instead.
    """
    from backend.processing.lazy_extraction import LazyExtractionService

    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(LazyExtractionService, "extract_on_demand", mock)
    return mock


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Each test starts with a clean rate-limit window."""
    limiter.reset()
    yield
    limiter.reset()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def api_key(setup_db) -> str:
    """A valid API key persisted in the test database."""
    key = generate_api_key()
    async with TestSessionLocal() as session:
        session.add(ApiKey(name="test", key_hash=hash_api_key(key), prefix=key[:8]))
        await session.commit()
    return key


@pytest_asyncio.fixture
async def client(api_key):
    """Authenticated test client — sends a valid X-API-Key on every request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": api_key},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def anon_client():
    """Unauthenticated client for exercising 401 paths."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
