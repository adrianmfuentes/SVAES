"""add is_system to verification_profile and allow nullable organization_id

Revision ID: y2z3w4v5u6a7
Revises: x1y2z3w4v5u6
Create Date: 2026-06-17 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'y2z3w4v5u6a7'
down_revision = 'x1y2z3w4v5u6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'verification_profile',
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.alter_column('verification_profile', 'organization_id', nullable=True)


def downgrade() -> None:
    op.alter_column('verification_profile', 'organization_id', nullable=False)
    op.drop_column('verification_profile', 'is_system')
