"""merge pending_task and artifact description branches

Revision ID: a1b2c3d4e5f9
Revises: a1b2c3d4e5f8, z1a2b3c4d5e6
Create Date: 2026-06-19 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f9'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f8', 'z1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
