"""Add created_by and updated_by audit columns to clinical_crisis_alerts

Revision ID: oo0123456789
Revises: nn9012345678
"""

import sqlalchemy as sa
from alembic import op

revision = "oo0123456789"
down_revision = "nn9012345678"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clinical_crisis_alerts", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("updated_by", sa.Uuid(), nullable=True))


def downgrade():
    op.drop_column("clinical_crisis_alerts", "updated_by")
    op.drop_column("clinical_crisis_alerts", "created_by")
