"""cascade_delete_org_and_user: fix account deletion FK violations

Revision ID: s7t8u9v0w1x2
Revises: r6s7t8u9v0w1
Create Date: 2026-06-30

Add ON DELETE CASCADE to all FK constraints that point at organization.id or
user.id without a cascade action. Without these, deleting an org (as part of
account deletion) raises an IntegrityError because child rows exist in
user_membership, connector_instance, project, verification_profile, api_key,
notification_channel, and custom_role. Deleting the user afterwards fails on
notification_subscription. Project deletion is also extended with a cascade on
release.project_id so the release chain (artifact, verification_result) is
cleaned up automatically.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "s7t8u9v0w1x2"
down_revision: Union[str, Sequence[str], None] = "r6s7t8u9v0w1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- org → user_membership ---
    op.drop_constraint("user_membership_organization_id_fkey", "user_membership", type_="foreignkey")
    op.create_foreign_key(
        "user_membership_organization_id_fkey",
        "user_membership", "organization",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )

    # --- org → connector_instance ---
    op.drop_constraint("connector_instance_organization_id_fkey", "connector_instance", type_="foreignkey")
    op.create_foreign_key(
        "connector_instance_organization_id_fkey",
        "connector_instance", "organization",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )

    # --- org → project ---
    op.drop_constraint("project_organization_id_fkey", "project", type_="foreignkey")
    op.create_foreign_key(
        "project_organization_id_fkey",
        "project", "organization",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )

    # --- project → release (completes the org→project→release cascade chain) ---
    op.drop_constraint("release_project_id_fkey", "release", type_="foreignkey")
    op.create_foreign_key(
        "release_project_id_fkey",
        "release", "project",
        ["project_id"], ["id"],
        ondelete="CASCADE",
    )

    # --- org → verification_profile ---
    op.drop_constraint("verification_profile_organization_id_fkey", "verification_profile", type_="foreignkey")
    op.create_foreign_key(
        "verification_profile_organization_id_fkey",
        "verification_profile", "organization",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )

    # --- org → api_key ---
    op.drop_constraint("api_key_organization_id_fkey", "api_key", type_="foreignkey")
    op.create_foreign_key(
        "api_key_organization_id_fkey",
        "api_key", "organization",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )

    # --- org → notification_channel ---
    op.drop_constraint("notification_channel_organization_id_fkey", "notification_channel", type_="foreignkey")
    op.create_foreign_key(
        "notification_channel_organization_id_fkey",
        "notification_channel", "organization",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )

    # --- org → custom_role ---
    op.drop_constraint("custom_role_organization_id_fkey", "custom_role", type_="foreignkey")
    op.create_foreign_key(
        "custom_role_organization_id_fkey",
        "custom_role", "organization",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )

    # --- user → notification_subscription ---
    op.drop_constraint("notification_subscription_user_id_fkey", "notification_subscription", type_="foreignkey")
    op.create_foreign_key(
        "notification_subscription_user_id_fkey",
        "notification_subscription", "user",
        ["user_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("notification_subscription_user_id_fkey", "notification_subscription", type_="foreignkey")
    op.create_foreign_key(
        "notification_subscription_user_id_fkey",
        "notification_subscription", "user",
        ["user_id"], ["id"],
    )

    op.drop_constraint("custom_role_organization_id_fkey", "custom_role", type_="foreignkey")
    op.create_foreign_key(
        "custom_role_organization_id_fkey",
        "custom_role", "organization",
        ["organization_id"], ["id"],
    )

    op.drop_constraint("notification_channel_organization_id_fkey", "notification_channel", type_="foreignkey")
    op.create_foreign_key(
        "notification_channel_organization_id_fkey",
        "notification_channel", "organization",
        ["organization_id"], ["id"],
    )

    op.drop_constraint("api_key_organization_id_fkey", "api_key", type_="foreignkey")
    op.create_foreign_key(
        "api_key_organization_id_fkey",
        "api_key", "organization",
        ["organization_id"], ["id"],
    )

    op.drop_constraint("verification_profile_organization_id_fkey", "verification_profile", type_="foreignkey")
    op.create_foreign_key(
        "verification_profile_organization_id_fkey",
        "verification_profile", "organization",
        ["organization_id"], ["id"],
    )

    op.drop_constraint("release_project_id_fkey", "release", type_="foreignkey")
    op.create_foreign_key(
        "release_project_id_fkey",
        "release", "project",
        ["project_id"], ["id"],
    )

    op.drop_constraint("project_organization_id_fkey", "project", type_="foreignkey")
    op.create_foreign_key(
        "project_organization_id_fkey",
        "project", "organization",
        ["organization_id"], ["id"],
    )

    op.drop_constraint("connector_instance_organization_id_fkey", "connector_instance", type_="foreignkey")
    op.create_foreign_key(
        "connector_instance_organization_id_fkey",
        "connector_instance", "organization",
        ["organization_id"], ["id"],
    )

    op.drop_constraint("user_membership_organization_id_fkey", "user_membership", type_="foreignkey")
    op.create_foreign_key(
        "user_membership_organization_id_fkey",
        "user_membership", "organization",
        ["organization_id"], ["id"],
    )
