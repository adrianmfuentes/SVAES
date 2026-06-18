"""add pending_task_id and previous_status to release

Revision ID: a1b2c3d4e5f8
Revises: y2z3w4v5u6a7
Create Date: 2026-06-18 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f8'
down_revision = 'y2z3w4v5u6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'release',
        sa.Column('pending_task_id', sa.String(100), nullable=True),
    )
    op.add_column(
        'release',
        sa.Column('previous_status', sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('release', 'previous_status')
    op.drop_column('release', 'pending_task_id')