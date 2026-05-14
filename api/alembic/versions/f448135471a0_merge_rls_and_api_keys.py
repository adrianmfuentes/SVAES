"""merge_rls_and_api_keys

Revision ID: f448135471a0
Revises: a1b2c3d4e5f6, b1c2d3e4f5g6
Create Date: 2026-05-14 22:45:12.741812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f448135471a0'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'b1c2d3e4f5g6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
