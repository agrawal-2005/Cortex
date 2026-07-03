from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


# --- Document schemas ---


class DocumentCreate(BaseModel):
    content: str
    source_type: str
    source_id: str
    source_link: Optional[str] = None
    source_label: Optional[str] = None
    channel_or_project: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    created_at: Optional[datetime] = None
    embedding_id: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    content: str
    source_type: str
    source_id: str
    source_link: Optional[str]
    source_label: Optional[str]
    channel_or_project: Optional[str]
    author_name: Optional[str]
    author_role: Optional[str]
    created_at: Optional[datetime]
    ingested_at: datetime
    embedding_id: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# --- Skill Step schemas ---


class SkillStepCreate(BaseModel):
    step_order: int
    action: str
    details: dict = {}
    confidence: float = 0.0
    depends_on: list[str] = []


class SkillStepResponse(BaseModel):
    id: str
    skill_id: str
    step_order: int
    action: str
    details: dict
    confidence: float
    depends_on: list

    model_config = ConfigDict(from_attributes=True)


# --- Skill schemas ---


class SkillCreate(BaseModel):
    name: str
    description: str
    department: Optional[str] = None
    skill_data: dict = {}
    steps: list[SkillStepCreate] = []


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    department: Optional[str]
    status: str
    confidence: float
    version: int
    skill_data: dict
    extracted_at: datetime
    verified_at: Optional[datetime]
    verified_by: Optional[str]
    steps: list[SkillStepResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    skill_data: Optional[dict] = None
    confidence: Optional[float] = None
    verified_by: Optional[str] = None


# --- Step Source schemas ---


class StepSourceCreate(BaseModel):
    step_id: str
    document_id: str
    relevance_score: float = 0.0
    snippet: str = ""


class StepSourceResponse(BaseModel):
    id: str
    step_id: str
    document_id: str
    relevance_score: float
    snippet: str

    model_config = ConfigDict(from_attributes=True)


# --- Feedback schemas ---


class FeedbackCreate(BaseModel):
    skill_id: str
    step_id: Optional[str] = None
    action: str  # approve, edit, reject
    original_content: Optional[str] = None
    corrected_content: Optional[str] = None
    reason: Optional[str] = None
    submitted_by: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    skill_id: str
    step_id: Optional[str]
    action: str
    original_content: Optional[str]
    corrected_content: Optional[str]
    reason: Optional[str]
    submitted_by: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Source Trust schemas ---


class SourceTrustResponse(BaseModel):
    source_identifier: str
    times_cited: int
    times_approved: int
    times_rejected: int
    trust_score: float
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Query schemas ---


class QueryRequest(BaseModel):
    question: str


class QuerySourceHit(BaseModel):
    document_id: str
    content_snippet: str
    source_type: str
    relevance: float


class MatchedDocument(BaseModel):
    """A relevant source document returned when no skill has been
    extracted for the topic yet."""

    preview: str
    source_type: str
    source_link: Optional[str] = None
    author: Optional[str] = None
    relevance: float


class QueryResponse(BaseModel):
    question: str
    skill: Optional[SkillResponse] = None
    readable_answer: str = ""
    source_hits: list[QuerySourceHit] = []
    matched_documents: list[MatchedDocument] = []
    suggestion: str = ""
    confidence: float = 0.0


# --- GitHub ingestion schemas ---


class GitHubIngestRequest(BaseModel):
    repo: str  # "owner/repo"
    token: Optional[str] = None  # falls back to GITHUB_TOKEN env var
    months: int = 6
    max_requests: Optional[int] = None  # default: 55 unauthenticated, 4000 with token
    include_comments: bool = True

    @field_validator("repo")
    @classmethod
    def _validate_repo(cls, v: str) -> str:
        from backend.security.validation import validate_repo

        return validate_repo(v)


# --- Discord ingestion schemas ---


class DiscordLiveIngestRequest(BaseModel):
    guild_id: str
    channel_ids: list[str]
    bot_token: Optional[str] = None  # falls back to DISCORD_BOT_TOKEN env var
    max_messages_per_channel: int = 1000


# --- Ingestion status schemas ---


class IngestStatusResponse(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    progress: Optional[dict] = None
    error: Optional[str] = None


# --- Paginated response ---


class PaginatedResponse(BaseModel):
    items: list
    total: int
    skip: int
    limit: int


# --- Health ---


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
