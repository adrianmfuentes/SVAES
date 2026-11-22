"""Create the template table used by the templates API."""

import sqlalchemy as sa
from alembic import op


revision = "t0u1v2w3x4y5"
down_revision = "r8s9t0u1v2w3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "template",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column(
            "profile_id", sa.Uuid(),
            sa.ForeignKey("verification_profile.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("project_name_template", sa.String(200)),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("template")
