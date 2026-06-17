"""remove_organization_plan

Revision ID: j8k9l0m1n2o3
Revises: i7j8k9l0m1n2
Create Date: 2026-05-30 15:56:27.105332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j8k9l0m1n2o3"
down_revision: Union[str, Sequence[str], None] = "i7j8k9l0m1n2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'organization' AND column_name = 'plan'"))
    if result.fetchone() is not None:
        op.drop_column("organization", "plan")


def downgrade() -> None:
    op.add_column("organization", sa.Column("plan", sa.String(50), nullable=True, server_default="default"))
