"""initial schema — tickets and logs tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("detected_language", sa.String(length=16), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("draft_reply", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('refund', 'technical_issue', 'billing', 'general_question', 'complaint')",
            name="ck_tickets_category_valid",
        ),
        sa.CheckConstraint(
            "priority IN ('urgent', 'normal')", name="ck_tickets_priority_valid"
        ),
        sa.CheckConstraint(
            "status IN ('auto_ready', 'manual_review')", name="ck_tickets_status_valid"
        ),
    )

    op.create_table(
        "logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("step_name", sa.String(length=64), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], ondelete="CASCADE", name="fk_logs_ticket_id"
        ),
    )
    op.create_index("ix_logs_ticket_id", "logs", ["ticket_id"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])
    op.create_index("ix_tickets_status", "tickets", ["status"])


def downgrade() -> None:
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_logs_ticket_id", table_name="logs")
    op.drop_table("logs")
    op.drop_table("tickets")
