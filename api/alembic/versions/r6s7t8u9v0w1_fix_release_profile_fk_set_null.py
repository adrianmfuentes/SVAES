"""fix release.profile_id FK: CASCADE -> SET NULL

Revision ID: r6s7t8u9v0w1
Revises: q5r6s7t8u9v0
Create Date: 2026-06-30

profile_id is nullable=True on release, meaning the association is optional and
releases should survive profile deletion. The previous CASCADE incorrectly deleted
all releases referencing a profile when that profile was removed.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "r6s7t8u9v0w1"
down_revision: Union[str, Sequence[str], None] = "q5r6s7t8u9v0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("release_profile_id_fkey", "release", type_="foreignkey")
    op.create_foreign_key(
        "release_profile_id_fkey",
        "release",
        "verification_profile",
        ["profile_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("release_profile_id_fkey", "release", type_="foreignkey")
    op.create_foreign_key(
        "release_profile_id_fkey",
        "release",
        "verification_profile",
        ["profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
