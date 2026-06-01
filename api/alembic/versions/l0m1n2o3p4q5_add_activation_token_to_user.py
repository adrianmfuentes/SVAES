"""add_activation_token_to_user

Revision ID: l0m1n2o3p4q5
Revises: k9l0m1n2o3p4
Create Date: 2026-05-31 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l0m1n2o3p4q5"
down_revision: Union[str, Sequence[str], None] = "k9l0m1n2o3p4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("activation_token", sa.String(255), nullable=True))
    op.add_column("user", sa.Column("activation_token_expiry", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_user_activation_token"), "user", ["activation_token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_activation_token"), table_name="user")
    op.drop_column("user", "activation_token_expiry")
    op.drop_column("user", "activation_token")
