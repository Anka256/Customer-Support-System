"""add other/irrelevant category

Revision ID: 0002_add_other_category
Revises: 0001_initial
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_add_other_category"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_CATEGORIES = "('refund', 'technical_issue', 'billing', 'general_question', 'complaint')"
_NEW_CATEGORIES = (
    "('refund', 'technical_issue', 'billing', 'general_question', 'complaint', 'other/irrelevant')"
)


def upgrade() -> None:
    op.drop_constraint("ck_tickets_category_valid", "tickets", type_="check")
    op.create_check_constraint(
        "ck_tickets_category_valid", "tickets", f"category IN {_NEW_CATEGORIES}"
    )


def downgrade() -> None:
    op.drop_constraint("ck_tickets_category_valid", "tickets", type_="check")
    op.create_check_constraint(
        "ck_tickets_category_valid", "tickets", f"category IN {_OLD_CATEGORIES}"
    )
