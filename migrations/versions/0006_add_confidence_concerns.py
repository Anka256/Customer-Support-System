"""add confidence_concerns column to tickets

Revision ID: 0006_add_confidence_concerns
Revises: 0005_add_log_raw_text
Create Date: 2026-07-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_add_confidence_concerns"
down_revision: Union[str, None] = "0005_add_log_raw_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("confidence_concerns", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "confidence_concerns")
