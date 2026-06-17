"""add ERROR to connector_status enum

Revision ID: x1y2z3w4v5u6
Revises: n2o3p4q5r6s7
Create Date: 2026-06-17 15:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'x1y2z3w4v5u6'
down_revision = 'n2o3p4q5r6s7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE connector_status ADD VALUE IF NOT EXISTS 'ERROR'")


def downgrade() -> None:
    pass
