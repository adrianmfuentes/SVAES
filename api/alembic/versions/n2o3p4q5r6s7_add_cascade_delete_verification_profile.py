"""add_cascade_delete_verification_profile: FK cascade delete

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-06-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n2o3p4q5r6s7"
down_revision: Union[str, Sequence[str], None] = "m1n2o3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "verification_rule_profile_id_fkey", "verification_rule", type_="foreignkey"
    )
    op.create_foreign_key(
        "verification_rule_profile_id_fkey",
        "verification_rule",
        "verification_profile",
        ["profile_id"],
        ["id"],
        ondelete="cascade",
    )
    op.drop_constraint(
        "release_profile_id_fkey", "release", type_="foreignkey"
    )
    op.create_foreign_key(
        "release_profile_id_fkey",
        "release",
        "verification_profile",
        ["profile_id"],
        ["id"],
        ondelete="cascade",
    )


def downgrade() -> None:
    op.drop_constraint(
        "verification_rule_profile_id_fkey", "verification_rule", type_="foreignkey"
    )
    op.create_foreign_key(
        "verification_rule_profile_id_fkey",
        "verification_rule",
        "verification_profile",
        ["profile_id"],
        ["id"],
    )
    op.drop_constraint(
        "release_profile_id_fkey", "release", type_="foreignkey"
    )
    op.create_foreign_key(
        "release_profile_id_fkey",
        "release",
        "verification_profile",
        ["profile_id"],
        ["id"],
    )
