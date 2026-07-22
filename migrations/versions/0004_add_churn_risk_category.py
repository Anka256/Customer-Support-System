"""add churn_risk category

Revision ID: 0004_add_churn_risk_category
Revises: 0003_add_reviewed_sent_status
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004_add_churn_risk_category"
down_revision: Union[str, None] = "0003_add_reviewed_sent_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_CATEGORIES = (
    "('refund', 'technical_issue', 'billing', 'general_question', 'complaint', 'other/irrelevant')"
)
_NEW_CATEGORIES = (
    "('refund', 'technical_issue', 'billing', 'general_question', 'complaint', "
    "'other/irrelevant', 'churn_risk')"
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
