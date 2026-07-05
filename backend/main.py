from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.schemas import HealthResponse
from backend.security.auth import require_api_key
from backend.security.ratelimit import ingest_rate_limit, query_rate_limit
from backend.ingestion.router import router as ingestion_router
from backend.ingestion.file_upload import router as file_upload_router
from backend.api.feedback import router as feedback_router
from backend.knowledge.router import router as knowledge_router
from backend.processing.router import router as processing_router
from backend.api.routes_ingest import router as routes_ingest_router
from backend.api.routes_skills import router as routes_skills_router
from backend.api.routes_query import router as routes_query_router
from backend.api.routes_feedback import router as routes_feedback_router
from backend.api.routes_sources import router as routes_sources_router
from backend.api.routes_data_overview import router as routes_data_overview_router
from backend.api.routes_workspace import router as routes_workspace_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: run startup/shutdown tasks."""
    await init_db()
    yield


app = FastAPI(
    title="Cortex API",
    description=(
        "Cortex extracts tribal knowledge from company tools, synthesizes it "
        "into structured workflows called skills, and serves them via API."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — localhost origins in dev; explicit CORS_ORIGINS in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every route (except /health and the docs) requires a valid X-API-Key.
_auth = [Depends(require_api_key)]
# POST ingestions and queries are additionally rate limited per API key.
_auth_ingest = [Depends(require_api_key), Depends(ingest_rate_limit)]
_auth_query = [Depends(require_api_key), Depends(query_rate_limit)]

# Include routers
app.include_router(ingestion_router, prefix="/api/v1/ingest", tags=["ingestion"], dependencies=_auth_ingest)
app.include_router(file_upload_router, prefix="/api/v1/ingest", tags=["ingestion"], dependencies=_auth_ingest)
app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["feedback"], dependencies=_auth)
app.include_router(knowledge_router, prefix="/api/v1/skills", tags=["skills"], dependencies=_auth)
app.include_router(processing_router, prefix="/api/v1/processing", tags=["processing"], dependencies=_auth)

# New API routes (/api/ prefix)
app.include_router(routes_ingest_router, prefix="/api/ingest", tags=["ingest-v2"], dependencies=_auth_ingest)
app.include_router(routes_skills_router, prefix="/api/skills", tags=["skills-v2"], dependencies=_auth)
app.include_router(routes_query_router, prefix="/api/query", tags=["query"], dependencies=_auth_query)
app.include_router(routes_feedback_router, prefix="/api/feedback", tags=["feedback-v2"], dependencies=_auth)
app.include_router(routes_sources_router, prefix="/api/sources", tags=["sources"], dependencies=_auth)
app.include_router(routes_data_overview_router, prefix="/api/data-overview", tags=["data-overview"], dependencies=_auth)
app.include_router(routes_workspace_router, prefix="/api/workspace", tags=["workspace"], dependencies=_auth)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )
