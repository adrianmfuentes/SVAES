"""add_user_id_to_api_key

Revision ID: g5h6i7j8k9l0
Revises: f448135471a0
Create Date: 2026-05-18 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g5h6i7j8k9l0"
down_revision: Union[str, Sequence[str], None] = "f4g5h6i7j8k9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_key",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "api_key_user_id_fkey", "api_key", "user", ["user_id"], ["id"]
    )
    op.create_index("ix_api_key_user_id", "api_key", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_key_user_id", table_name="api_key")
    op.drop_constraint("api_key_user_id_fkey", "api_key", type_="foreignkey")
    op.drop_column("api_key", "user_id")
