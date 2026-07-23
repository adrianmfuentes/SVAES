"""add_webhook_fields_to_connector_instance: inbound webhook secret + toggle for source-control connectors

Revision ID: q7r8s9t0u1v2
Revises: p3q4r5s6t7u8
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q7r8s9t0u1v2"
down_revision: Union[str, Sequence[str], None] = "p3q4r5s6t7u8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "connector_instance",
        sa.Column("webhook_secret_encrypted", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "connector_instance",
        sa.Column("webhook_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("connector_instance", "webhook_enabled")
    op.drop_column("connector_instance", "webhook_secret_encrypted")
