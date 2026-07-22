"""add raw_text column to logs for rejected-ticket audit visibility

Revision ID: 0005_add_log_raw_text
Revises: 0004_add_churn_risk_category
Create Date: 2026-07-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_add_log_raw_text"
down_revision: Union[str, None] = "0004_add_churn_risk_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("logs", sa.Column("raw_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("logs", "raw_text")
