"""backfill_user_membership: populate multi-org membership table from user.organization_id

Revision ID: u9v0x1y2z3a4b
Revises: t8u9v0w1x2y3
Create Date: 2026-07-01

The user_membership table has existed since the initial schema but was never
written to by the application (users had a single organization_id/role on the
user table). This migration backfills one membership row per user that
currently has an organization_id set, using their current role, so that the
existing single-org relationship becomes the user's first membership under
the new multi-org model. No schema changes: the table and its columns/unique
constraint already exist.

UUIDs are generated in Python (not gen_random_uuid()) since pgcrypto is not
guaranteed to be enabled on every deployment target.
"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "u9v0x1y2z3a4b"
down_revision: Union[str, Sequence[str], None] = "t8u9v0w1x2y3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    users = bind.execute(
        sa.text(
            'SELECT u.id, u.organization_id, u.role '
            'FROM "user" u '
            'INNER JOIN organization o ON o.id = u.organization_id '
            'WHERE u.organization_id IS NOT NULL'
        )
    ).fetchall()

    for user_id, organization_id, role in users:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM user_membership WHERE user_id = :user_id AND organization_id = :organization_id"
            ),
            {"user_id": user_id, "organization_id": organization_id},
        ).fetchone()
        if exists:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO user_membership (id, organization_id, user_id, role, created_at)
                VALUES (:id, :organization_id, :user_id, :role, now())
                """
            ),
            {
                "id": uuid.uuid4(),
                "organization_id": organization_id,
                "user_id": user_id,
                "role": role,
            },
        )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM user_membership um
        USING "user" u
        WHERE um.user_id = u.id
          AND um.organization_id = u.organization_id
          AND um.role::text = u.role::text
        """
    )
