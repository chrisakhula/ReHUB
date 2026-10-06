"""merge heads

Revision ID: 274c7a9e6ac8
Revises: 97aaaf694216, jj5678901234
"""
from alembic import op
import sqlalchemy as sa


revision = '274c7a9e6ac8'
down_revision = ('97aaaf694216', 'jj5678901234')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
