"""add_schedule_to_verification_profile: cron expression for scheduled verifications

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-07-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r8s9t0u1v2w3"
down_revision: Union[str, Sequence[str], None] = "q7r8s9t0u1v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "verification_profile",
        sa.Column("schedule", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "verification_profile",
        sa.Column("schedule_last_run_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("verification_profile", "schedule_last_run_at")
    op.drop_column("verification_profile", "schedule")
