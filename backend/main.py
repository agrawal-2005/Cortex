from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.schemas import HealthResponse
from backend.ingestion.router import router as ingestion_router
from backend.ingestion.file_upload import router as file_upload_router
from backend.api.feedback import router as feedback_router
from backend.knowledge.router import router as knowledge_router
from backend.processing.router import router as processing_router
from backend.api.routes_ingest import router as routes_ingest_router
from backend.api.routes_skills import router as routes_skills_router
from backend.api.routes_query import router as routes_query_router
from backend.api.routes_feedback import router as routes_feedback_router


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

# CORS middleware — allow all origins in dev mode
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion_router, prefix="/api/v1/ingest", tags=["ingestion"])
app.include_router(file_upload_router, prefix="/api/v1/ingest", tags=["ingestion"])
app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(knowledge_router, prefix="/api/v1/skills", tags=["skills"])
app.include_router(processing_router, prefix="/api/v1/processing", tags=["processing"])

# New API routes (/api/ prefix)
app.include_router(routes_ingest_router, prefix="/api/ingest", tags=["ingest-v2"])
app.include_router(routes_skills_router, prefix="/api/skills", tags=["skills-v2"])
app.include_router(routes_query_router, prefix="/api/query", tags=["query"])
app.include_router(routes_feedback_router, prefix="/api/feedback", tags=["feedback-v2"])


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )
