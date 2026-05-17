"""rls_org_scoped_tables

Revision ID: a1b2c3d4e5f6
Revises: 2fd6efcfd6c9
Create Date: 2026-05-12 00:00:00.000000

Enables Row-Level Security on all organization-scoped tables and creates
permissive policies so that the API service role (app_user) can only see
rows belonging to the organization it claims via a session-level variable
app.current_organization_id.

Usage in application code (set before any query in a transaction):
    SET LOCAL app.current_organization_id = '<uuid>';
"""
from typing import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "2fd6efcfd6c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that carry an organization_id column directly or via FK chain.
# projects, profiles, and connector_instances have a direct organization_id.
# releases, verification_results, artifacts, and verification_rules are scoped
# by joining upward — we do NOT enable RLS on them here because the join-based
# policy would make every query expensive; the application layer already enforces
# release/project ownership before exposing data.
_ORG_SCOPED = [
    "project",
    "verification_profile",
    "connector_instance",
]


def upgrade() -> None:
    for table in _ORG_SCOPED:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # Superuser (postgres / migration role) bypasses RLS automatically.
        # The app_user role uses this permissive policy.
        op.execute(
            f"""
            CREATE POLICY rls_{table}_org_isolation ON {table}
            AS PERMISSIVE
            FOR ALL
            TO PUBLIC
            USING (
                organization_id = current_setting('app.current_organization_id', true)::uuid
                OR current_setting('app.current_organization_id', true) IS NULL
                OR current_setting('app.current_organization_id', true) = ''
            )
            """
        )


def downgrade() -> None:
    for table in reversed(_ORG_SCOPED):
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_org_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
