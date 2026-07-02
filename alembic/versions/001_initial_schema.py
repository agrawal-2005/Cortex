"""Initial database schema.

Revision ID: 001
Revises: None
Create Date: 2025-07-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("source_link", sa.Text, nullable=True),
        sa.Column("source_label", sa.Text, nullable=True),
        sa.Column("channel_or_project", sa.String(255), nullable=True),
        sa.Column("author_name", sa.String(255), nullable=True),
        sa.Column("author_role", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("ingested_at", sa.DateTime, nullable=False),
        sa.Column("embedding_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_documents_source_type", "documents", ["source_type"])
    op.create_index("ix_documents_channel", "documents", ["channel_or_project"])

    # Skills
    op.create_table(
        "skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("skill_data", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("extracted_at", sa.DateTime, nullable=False),
        sa.Column("verified_at", sa.DateTime, nullable=True),
        sa.Column("verified_by", sa.String(255), nullable=True),
    )
    op.create_index("ix_skills_status", "skills", ["status"])
    op.create_index("ix_skills_department", "skills", ["department"])

    # Skill Steps
    op.create_table(
        "skill_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "skill_id",
            sa.String(36),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("details", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("depends_on", sa.JSON, nullable=False, server_default="[]"),
    )
    op.create_index("ix_skill_steps_skill_id", "skill_steps", ["skill_id"])

    # Step Sources
    op.create_table(
        "step_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "step_id",
            sa.String(36),
            sa.ForeignKey("skill_steps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relevance_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("snippet", sa.Text, nullable=False, server_default=""),
    )
    op.create_index("ix_step_sources_step_id", "step_sources", ["step_id"])
    op.create_index("ix_step_sources_document_id", "step_sources", ["document_id"])

    # Feedback
    op.create_table(
        "feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "skill_id",
            sa.String(36),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "step_id",
            sa.String(36),
            sa.ForeignKey("skill_steps.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("original_content", sa.Text, nullable=True),
        sa.Column("corrected_content", sa.Text, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("submitted_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_feedback_skill_id", "feedback", ["skill_id"])

    # Source Trust
    op.create_table(
        "source_trust",
        sa.Column("source_identifier", sa.String(500), primary_key=True),
        sa.Column("times_cited", sa.Integer, nullable=False, server_default="0"),
        sa.Column("times_approved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("times_rejected", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trust_score", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("last_updated", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("source_trust")
    op.drop_table("feedback")
    op.drop_table("step_sources")
    op.drop_table("skill_steps")
    op.drop_table("skills")
    op.drop_table("documents")
