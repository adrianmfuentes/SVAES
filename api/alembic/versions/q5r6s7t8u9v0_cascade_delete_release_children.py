"""cascade delete on artifact and verification_result when release is deleted

Revision ID: q5r6s7t8u9v0
Revises: p4q5r6s7t8u9
Create Date: 2026-06-21

"""
from alembic import op

revision = 'q5r6s7t8u9v0'
down_revision = 'p4q5r6s7t8u9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("artifact_release_id_fkey", "artifact", type_="foreignkey")
    op.create_foreign_key(
        "artifact_release_id_fkey",
        "artifact", "release",
        ["release_id"], ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("verification_result_release_id_fkey", "verification_result", type_="foreignkey")
    op.create_foreign_key(
        "verification_result_release_id_fkey",
        "verification_result", "release",
        ["release_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("verification_result_release_id_fkey", "verification_result", type_="foreignkey")
    op.create_foreign_key(
        "verification_result_release_id_fkey",
        "verification_result", "release",
        ["release_id"], ["id"],
    )

    op.drop_constraint("artifact_release_id_fkey", "artifact", type_="foreignkey")
    op.create_foreign_key(
        "artifact_release_id_fkey",
        "artifact", "release",
        ["release_id"], ["id"],
    )
