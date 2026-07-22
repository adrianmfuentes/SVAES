"""add_token_version_widen_totp_secret: session revocation + encrypted TOTP secret support

Revision ID: p3q4r5s6t7u8
Revises: w2x3y4z5a6b7
Create Date: 2026-07-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p3q4r5s6t7u8"
down_revision: Union[str, Sequence[str], None] = "w2x3y4z5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    # totp_secret now stores a Fernet-encrypted value instead of the raw base32
    # secret; ciphertext is longer than the original 64-char column.
    op.alter_column(
        "user",
        "totp_secret",
        existing_type=sa.String(64),
        type_=sa.String(255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "user",
        "totp_secret",
        existing_type=sa.String(255),
        type_=sa.String(64),
        existing_nullable=True,
    )
    op.drop_column("user", "token_version")
