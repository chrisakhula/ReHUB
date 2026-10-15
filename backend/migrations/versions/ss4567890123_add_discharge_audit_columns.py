"""Add created_by and updated_by audit columns to discharge tables.

Revision ID: ss4567890123
Revises: rr3456789012
Create Date: 2026-10-12 17:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'ss4567890123'
down_revision = 'rr3456789012'
branch_labels = None
depends_on = None

DISCHARGE_TABLES = [
    'discharge_plans',
    'discharge_aftercare_cases',
    'discharge_aftercare_contacts',
    'discharge_relapse_records',
]


def upgrade() -> None:
    for tbl in DISCHARGE_TABLES:
        op.add_column(tbl, sa.Column('created_by', sa.UUID(), sa.ForeignKey('users.id'), nullable=True))
        op.add_column(tbl, sa.Column('updated_by', sa.UUID(), sa.ForeignKey('users.id'), nullable=True))


def downgrade() -> None:
    for tbl in DISCHARGE_TABLES:
        op.drop_column(tbl, 'updated_by')
        op.drop_column(tbl, 'created_by')
