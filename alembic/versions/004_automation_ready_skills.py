"""Add automation-readiness fields to skills.

The skill evaluation showed skill_steps.details (already JSONB, no DDL
needed) and the skills table can't describe automation-ready workflows.
Adds skill-level trigger, inputs_schema, automation_readiness, and
is_repeatable columns. Existing rows get empty defaults and keep working.

Revision ID: 004
Revises: 003
Create Date: 2026-07-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("skills", sa.Column("trigger", sa.JSON, nullable=True))
    op.add_column(
        "skills",
        sa.Column("inputs_schema", sa.JSON, nullable=False, server_default="{}"),
    )
    op.add_column(
        "skills",
        sa.Column(
            "automation_readiness", sa.JSON, nullable=False, server_default="{}"
        ),
    )
    op.add_column(
        "skills",
        sa.Column(
            "is_repeatable", sa.Boolean, nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("skills", "is_repeatable")
    op.drop_column("skills", "automation_readiness")
    op.drop_column("skills", "inputs_schema")
    op.drop_column("skills", "trigger")
