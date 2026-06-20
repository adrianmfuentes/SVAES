"""fix verdict column type: drop pg enum, use varchar

Revision ID: o3p4q5r6s7t8
Revises: z1a2b3c4d5e6
Create Date: 2026-06-20

The initial migration created verification_result.verdict as a PostgreSQL native
enum type (verdict_type) with Spanish values (VALIDO, CON_ADVERTENCIAS, NO_VALIDO).
The application code stores English values (VALID, VALID_WITH_WARNINGS, INVALID) via
a String(30) column — causing a DatatypeMismatch on INSERT. This migration converts
the column to VARCHAR(30) so the ORM can write freely.
"""
from alembic import op
import sqlalchemy as sa


revision = 'o3p4q5r6s7t8'
down_revision = 'a1b2c3d4e5f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert the enum column to plain VARCHAR so the ORM can insert string values.
    # Using USING cast to coerce any existing enum values.
    op.execute(
        "ALTER TABLE verification_result "
        "ALTER COLUMN verdict TYPE VARCHAR(30) USING verdict::text"
    )
    # Drop the now-unused enum type
    op.execute("DROP TYPE IF EXISTS verdict_type")


def downgrade() -> None:
    # Recreate the original enum and cast back (values may not round-trip perfectly)
    op.execute(
        "CREATE TYPE verdict_type AS ENUM ('VALIDO', 'CON_ADVERTENCIAS', 'NO_VALIDO')"
    )
    op.execute(
        "ALTER TABLE verification_result "
        "ALTER COLUMN verdict TYPE verdict_type USING verdict::verdict_type"
    )
