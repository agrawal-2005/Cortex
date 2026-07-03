"""Add skill_documents cluster-provenance table.

Links every document in a skill's source cluster to the skill, so the
query route can map any relevant document back to its skill — not just
the few documents the LLM cited in step_sources.

Revision ID: 002
Revises: 001
Create Date: 2026-07-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skill_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "skill_id",
            sa.String(36),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("skill_id", "document_id"),
    )
    op.create_index("ix_skill_documents_skill_id", "skill_documents", ["skill_id"])
    op.create_index(
        "ix_skill_documents_document_id", "skill_documents", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_skill_documents_document_id", table_name="skill_documents")
    op.drop_index("ix_skill_documents_skill_id", table_name="skill_documents")
    op.drop_table("skill_documents")
