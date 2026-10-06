"""Add CrisisAlert model

Revision ID: ff1234567890
Revises: ea1c6a40ca6b
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'ff1234567890'
down_revision = 'ea1c6a40ca6b'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('clinical_crisis_alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=True),
        sa.Column('source_entity', sa.String(length=50), nullable=False),
        sa.Column('source_entity_id', sa.String(length=50), nullable=False),
        sa.Column('detected_keywords', sa.String(length=500), nullable=False),
        sa.Column('text_snippet', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('acknowledged_by', sa.UUID(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clinical_crisis_alerts_client_id'), 'clinical_crisis_alerts', ['client_id'], unique=False)
    op.create_index(op.f('ix_clinical_crisis_alerts_facility_id'), 'clinical_crisis_alerts', ['facility_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_clinical_crisis_alerts_facility_id'), table_name='clinical_crisis_alerts')
    op.drop_index(op.f('ix_clinical_crisis_alerts_client_id'), table_name='clinical_crisis_alerts')
    op.drop_table('clinical_crisis_alerts')
