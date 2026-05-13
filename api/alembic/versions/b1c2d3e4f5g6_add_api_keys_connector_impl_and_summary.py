"""add_api_keys_connector_impl_and_summary

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f7
Create Date: 2026-05-13 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b1c2d3e4f5g6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "connector_instance",
        sa.Column("connector_implementation", sa.String(50), nullable=False, server_default="JIRA"),
    )
    op.add_column(
        "artifact",
        sa.Column("connector_implementation", sa.String(50), nullable=False, server_default="JIRA"),
    )
    op.add_column(
        "verification_result",
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        "api_key",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(256), nullable=False, unique=True),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_key_organization_id", "api_key", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_key_organization_id", table_name="api_key")
    op.drop_table("api_key")
    op.drop_column("verification_result", "summary")
    op.drop_column("artifact", "connector_implementation")
    op.drop_column("connector_instance", "connector_implementation")