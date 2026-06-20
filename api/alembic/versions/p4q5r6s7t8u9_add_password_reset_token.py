"""add password_reset_token to user

Revision ID: p4q5r6s7t8u9
Revises: o3p4q5r6s7t8
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa


revision = 'p4q5r6s7t8u9'
down_revision = 'o3p4q5r6s7t8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('user', sa.Column('password_reset_token_expiry', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_user_password_reset_token', 'user', ['password_reset_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_user_password_reset_token', table_name='user')
    op.drop_column('user', 'password_reset_token_expiry')
    op.drop_column('user', 'password_reset_token')
