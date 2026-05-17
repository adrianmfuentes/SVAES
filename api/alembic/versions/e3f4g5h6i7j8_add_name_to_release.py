"""add_name_to_release

Revision ID: e3f4g5h6i7j8
Revises: d2e3f4g5h6i7
Create Date: 2026-05-17 00:00:02.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e3f4g5h6i7j8'
down_revision: Union[str, Sequence[str]] = 'd2e3f4g5h6i7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('release', sa.Column('name', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('release', 'name')
