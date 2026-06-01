"""create_access_request_table

Revision ID: k9l0m1n2o3p4
Revises: j8k9l0m1n2o3
Create Date: 2026-05-31 08:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k9l0m1n2o3p4"
down_revision: Union[str, Sequence[str], None] = "j8k9l0m1n2o3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "access_request",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("requester_name", sa.String(100), nullable=False),
        sa.Column("requester_email", sa.String(255), nullable=False),
        sa.Column("organization_name", sa.String(100), nullable=False),
        sa.Column("organization_description", sa.String(500), nullable=True),
        sa.Column("slug_preview", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_access_request_requester_email"), "access_request", ["requester_email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_access_request_requester_email"), table_name="access_request")
    op.drop_table("access_request")
