"""add_rules_to_verification_profile

Revision ID: c1d2e3f4g5h6
Revises: f448135471a0
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, Sequence[str]] = 'f448135471a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'verification_profile',
        sa.Column('rules', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('verification_profile', 'rules')
