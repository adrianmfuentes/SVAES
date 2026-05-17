"""add_missing_project_columns

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2026-05-17 00:00:01.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd2e3f4g5h6i7'
down_revision: Union[str, Sequence[str]] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project', sa.Column('profile_id', sa.UUID(), nullable=True))
    op.add_column('project', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('project', 'is_archived')
    op.drop_column('project', 'profile_id')
