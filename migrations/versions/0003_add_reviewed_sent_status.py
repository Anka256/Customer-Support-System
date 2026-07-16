"""add reviewed_sent status

Revision ID: 0003_add_reviewed_sent_status
Revises: 0002_add_other_category
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003_add_reviewed_sent_status"
down_revision: Union[str, None] = "0002_add_other_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_STATUSES = "('auto_ready', 'manual_review')"
_NEW_STATUSES = "('auto_ready', 'manual_review', 'reviewed_sent')"


def upgrade() -> None:
    op.drop_constraint("ck_tickets_status_valid", "tickets", type_="check")
    op.create_check_constraint(
        "ck_tickets_status_valid", "tickets", f"status IN {_NEW_STATUSES}"
    )


def downgrade() -> None:
    op.drop_constraint("ck_tickets_status_valid", "tickets", type_="check")
    op.create_check_constraint(
        "ck_tickets_status_valid", "tickets", f"status IN {_OLD_STATUSES}"
    )
