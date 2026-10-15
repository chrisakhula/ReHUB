"""Add created_by and updated_by audit columns to compliance and residential tables.

Revision ID: uu6789012345
Revises: tt5678901234
Create Date: 2026-10-15 21:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'uu6789012345'
down_revision = 'tt5678901234'
branch_labels = None
depends_on = None

AUDIT_TABLES = [
    'compliance_registers',
    'compliance_inspections',
    'residential_movements',
    'residential_visitors',
    'residential_visitor_logs',
    'residential_grievances',
    'residential_meal_plans',
]


def upgrade() -> None:
    for tbl in AUDIT_TABLES:
        op.add_column(tbl, sa.Column('created_by', sa.UUID(), sa.ForeignKey('users.id'), nullable=True))
        op.add_column(tbl, sa.Column('updated_by', sa.UUID(), sa.ForeignKey('users.id'), nullable=True))


def downgrade() -> None:
    for tbl in AUDIT_TABLES:
        op.drop_column(tbl, 'updated_by')
        op.drop_column(tbl, 'created_by')
