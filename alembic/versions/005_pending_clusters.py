"""Add pending_clusters table for lazy extraction.

On ingestion every document is clustered, but only the largest
PRE_EXTRACT_TOP_N clusters are extracted immediately. The remaining
clusters are stored here (metadata only) and extracted on demand the
first time a query matches one of their documents.

Revision ID: 005
Revises: 004
Create Date: 2026-07-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_clusters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("document_ids", sa.JSON(), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column(
            "skill_id",
            sa.String(36),
            sa.ForeignKey("skills.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("extracted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_pending_clusters_status", "pending_clusters", ["status"])


def downgrade() -> None:
    op.drop_index("ix_pending_clusters_status", table_name="pending_clusters")
    op.drop_table("pending_clusters")
