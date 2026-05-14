"""rbac_and_security_fields

Revision ID: a1b2c3d4e5f7
Revises: 2fd6efcfd6c9
Create Date: 2026-05-13 12:00:00.000000

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f7'
down_revision: str | Sequence[str] | None = '2fd6efcfd6c9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('user', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organization', sa.Column('owner_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_org_owner', 'organization', 'user', ['owner_id'], ['id'])
    op.alter_column('user', 'password_hash', new_column_name='hashed_password')
    op.alter_column('verification_rule', 'severity',
        existing_type=sa.Enum('OBLIGATORIA', 'RECOMENDADA', 'INFORMATIVA', name='severity_type'),
        type_=sa.Enum('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='severity_type'),
        postgresql_using='severity::text'
    )
    op.create_table('custom_role',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('permissions', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name')
    )


def downgrade() -> None:
    op.drop_table('custom_role')
    op.alter_column('verification_rule', 'severity',
        existing_type=sa.Enum('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='severity_type'),
        type_=sa.Enum('OBLIGATORIA', 'RECOMENDADA', 'INFORMATIVA', name='severity_type'),
        postgresql_using='severity::text'
    )
    op.alter_column('user', 'hashed_password', new_column_name='password_hash')
    op.drop_constraint('fk_org_owner', 'organization', type_='foreignkey')
    op.drop_column('organization', 'owner_id')
    op.drop_column('user', 'locked_until')
    op.drop_column('user', 'failed_login_attempts')