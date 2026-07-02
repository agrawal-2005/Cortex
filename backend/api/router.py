from fastapi import APIRouter

from backend.ingestion.router import router as ingestion_router
from backend.api.feedback import router as feedback_router

api_router = APIRouter()

api_router.include_router(ingestion_router, prefix="/ingest", tags=["ingestion"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["feedback"])

# The knowledge router will be included once backend/knowledge/router.py is built.
# from backend.knowledge.router import router as knowledge_router
# api_router.include_router(knowledge_router, prefix="/skills", tags=["skills"])
