"""Add created_by and updated_by audit columns to residential tables

Revision ID: rr3456789012
Revises: qq2345678901
"""

import sqlalchemy as sa
from alembic import op

revision = "rr3456789012"
down_revision = "qq2345678901"
branch_labels = None
depends_on = None


def upgrade():
    tables = [
        "residential_incidents",
        "residential_incident_addenda",
        "residential_safeguarding_records",
    ]
    for tbl in tables:
        op.add_column(tbl, sa.Column("created_by", sa.Uuid(), nullable=True))
        op.add_column(tbl, sa.Column("updated_by", sa.Uuid(), nullable=True))


def downgrade():
    tables = [
        "residential_incidents",
        "residential_incident_addenda",
        "residential_safeguarding_records",
    ]
    for tbl in tables:
        op.drop_column(tbl, "updated_by")
        op.drop_column(tbl, "created_by")
