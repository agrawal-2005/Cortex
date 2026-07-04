import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, JSON, Float, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    content: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50))  # slack, jira, notion, csv, json
    source_id: Mapped[str] = mapped_column(String(255))
    source_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_or_project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(default=_utcnow)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    step_sources: Mapped[list["StepSource"]] = relationship(back_populates="document")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, review, verified, outdated, rejected-not-repeatable
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    skill_data: Mapped[dict] = mapped_column(JSON, default=dict)  # full executable skill as JSONB
    # How the skill is initiated:
    #   {"type": "event|manual|scheduled", "condition": "...", "event_binding": "..."}
    trigger: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Parameters the skill needs before it can run:
    #   {"param": "description and format"}
    inputs_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"level": "executable|assisted|reference", "safe_to_automate": bool,
    #  "missing_for_automation": [...], "requires_human_review": [...]}
    automation_readiness: Mapped[dict] = mapped_column(JSON, default=dict)
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=False)
    extracted_at: Mapped[datetime] = mapped_column(default=_utcnow)
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    steps: Mapped[list["SkillStep"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", order_by="SkillStep.step_order"
    )
    feedback: Mapped[list["Feedback"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan",
        foreign_keys="Feedback.skill_id",
    )


class SkillStep(Base):
    __tablename__ = "skill_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))
    step_order: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(Text)
    # Automation-ready step payload (all keys optional; older skills may only
    # have "explanation"):
    #   {
    #     "explanation": "human-readable description",
    #     "tool": {"name": "...", "method": "...", "auth_required": "..."},
    #     "inputs_required": ["repo", "pr_number", ...],
    #     "parameters": {"key": "value or template like {{input.repo}}"},
    #     "command": "literal command string if applicable",
    #     "expected_output": "what success returns",
    #     "success_criteria": "machine-checkable condition",
    #     "on_failure": [{"if": "...", "then": "...", "target": "..."}],
    #     "branch": {"if": "...", "then": "goto step X"},
    #     "approval_gate": {"if": "...", "require": "who approves"},
    #   }
    details: Mapped[dict] = mapped_column(JSON, default=dict)  # JSONB
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)  # UUID array stored as JSON

    # Relationships
    skill: Mapped["Skill"] = relationship(back_populates="steps")
    sources: Mapped[list["StepSource"]] = relationship(back_populates="step", cascade="all, delete-orphan")
    feedback: Mapped[list["Feedback"]] = relationship(
        back_populates="step", cascade="all, delete-orphan",
        foreign_keys="Feedback.step_id",
    )


class StepSource(Base):
    __tablename__ = "step_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    step_id: Mapped[str] = mapped_column(String(36), ForeignKey("skill_steps.id", ondelete="CASCADE"))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    snippet: Mapped[str] = mapped_column(Text, default="")

    # Relationships
    step: Mapped["SkillStep"] = relationship(back_populates="sources")
    document: Mapped["Document"] = relationship(back_populates="step_sources")


class SkillDocument(Base):
    """Cluster-level provenance: every document in the source cluster a skill
    was extracted from, not just the few the LLM cited in step_sources.

    Lets the query route map any relevant document back to its skill.
    """

    __tablename__ = "skill_documents"
    __table_args__ = (UniqueConstraint("skill_id", "document_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("skills.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )


class PendingCluster(Base):
    """A topic cluster that was identified at ingestion time but NOT
    extracted (lazy extraction only pre-extracts the largest clusters).

    Holds cluster metadata only — no LLM call has been made. When a query
    matches one of its documents, the cluster is extracted live, the skill
    is cached, and status flips to "extracted" so it is never re-extracted.
    """

    __tablename__ = "pending_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    cluster_id: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(500))
    document_ids: Mapped[list] = mapped_column(JSON, default=list)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True
    )  # pending, extracted
    skill_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    extracted_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))
    step_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("skill_steps.id", ondelete="CASCADE"), nullable=True)
    action: Mapped[str] = mapped_column(String(50))  # approve, edit, reject
    original_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    # Relationships
    skill: Mapped["Skill"] = relationship(back_populates="feedback", foreign_keys=[skill_id])
    step: Mapped["SkillStep | None"] = relationship(back_populates="feedback", foreign_keys=[step_id])


class ApiKey(Base):
    """API keys for authenticating requests. Only the SHA-256 hash of the
    key is stored — the plaintext is shown once at creation time."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prefix: Mapped[str] = mapped_column(String(12))  # first chars, for display
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class ConnectedSource(Base):
    """A configured external source (GitHub repo, Discord guild, ...) whose
    access token is stored Fernet-encrypted. The token is never returned by
    the API after creation."""

    __tablename__ = "connected_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))  # github, discord, slack
    encrypted_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # repo, guild_id, ...
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class SourceTrust(Base):
    __tablename__ = "source_trust"

    source_identifier: Mapped[str] = mapped_column(String(500), primary_key=True)
    times_cited: Mapped[int] = mapped_column(Integer, default=0)
    times_approved: Mapped[int] = mapped_column(Integer, default=0)
    times_rejected: Mapped[int] = mapped_column(Integer, default=0)
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    last_updated: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)
