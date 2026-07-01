"""seed_rv07_plan_default: default RV-07 to artifact_type=PLAN on the existing system profile

Revision ID: w2x3y4z5a6b7
Revises: v1a2b3c4d5e6f
Create Date: 2026-07-01

RV-07 ("Release planificada") without a configured `artifact_type` can never
pass: no connector exposes a generic "external_registered" marker to search
for across all artifact types. The engine now treats a PLAN-type artifact's
mere existence as sufficient proof of external registration (it comes from a
planning-tool connector like ClickUp by definition), and defaults new system
profiles to `{"artifact_type": "PLAN"}` for RV-07.

This data migration applies that same default to the RV-07 rule row of any
system profile seeded before this change (seeding only runs once, so existing
deployments would otherwise keep the old empty params forever). Only rows
that still have the original empty params are touched, so any org that has
already customized this rule via a duplicated profile is untouched (system
profile rules aren't editable in place, so in practice this only affects the
one seeded row).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "w2x3y4z5a6b7"
down_revision: Union[str, Sequence[str], None] = "v1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE verification_rule
            SET params = '{"artifact_type": "PLAN"}'
            WHERE rule_template = 'RV-07'
              AND (params IS NULL OR CAST(params AS TEXT) IN ('{}', 'null'))
              AND profile_id IN (
                  SELECT id FROM verification_profile WHERE is_system = true
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE verification_rule
            SET params = '{}'
            WHERE rule_template = 'RV-07'
              AND CAST(params AS TEXT) = '{"artifact_type": "PLAN"}'
              AND profile_id IN (
                  SELECT id FROM verification_profile WHERE is_system = true
              )
            """
        )
    )
