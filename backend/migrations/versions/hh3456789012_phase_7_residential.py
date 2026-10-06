"""phase_7_residential

Revision ID: hh3456789012
Revises: gg2345678901
Create Date: 2026-10-06 11:21:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'hh3456789012'
down_revision = 'gg2345678901'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We first drop old `incidents`, `resident_movements`, `visitors` if they exist
    # from previous partial implementations.
    op.execute("DROP TABLE IF EXISTS incidents CASCADE")
    op.execute("DROP TABLE IF EXISTS resident_movements CASCADE")
    op.execute("DROP TABLE IF EXISTS visitors CASCADE")

    # residential_movements
    op.create_table('residential_movements',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=False),
        sa.Column('movement_type', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expected_return', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('destination', sa.String(length=200), nullable=False),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_residential_movements_admission_id'), 'residential_movements', ['admission_id'], unique=False)
    op.create_index(op.f('ix_residential_movements_facility_id'), 'residential_movements', ['facility_id'], unique=False)

    # residential_visitors
    op.create_table('residential_visitors',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('relationship_to_client', sa.String(length=100), nullable=False),
        sa.Column('id_number', sa.String(length=100), nullable=False),
        sa.Column('contact_phone', sa.String(length=50), nullable=False),
        sa.Column('approved', sa.Boolean(), nullable=False),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_residential_visitors_client_id'), 'residential_visitors', ['client_id'], unique=False)
    op.create_index(op.f('ix_residential_visitors_facility_id'), 'residential_visitors', ['facility_id'], unique=False)

    # residential_visitor_logs
    op.create_table('residential_visitor_logs',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('visitor_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=True),
        sa.Column('check_in', sa.DateTime(timezone=True), nullable=False),
        sa.Column('check_out', sa.DateTime(timezone=True), nullable=True),
        sa.Column('items_brought_in', sa.Text(), nullable=False),
        sa.Column('visit_notes', sa.Text(), nullable=False),
        sa.Column('incidents_during_visit', sa.Boolean(), nullable=False),
        sa.Column('staff_authorizing_entry', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['staff_authorizing_entry'], ['users.id'], ),
        sa.ForeignKeyConstraint(['visitor_id'], ['residential_visitors.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_residential_visitor_logs_admission_id'), 'residential_visitor_logs', ['admission_id'], unique=False)
    op.create_index(op.f('ix_residential_visitor_logs_facility_id'), 'residential_visitor_logs', ['facility_id'], unique=False)
    op.create_index(op.f('ix_residential_visitor_logs_visitor_id'), 'residential_visitor_logs', ['visitor_id'], unique=False)

    # residential_incidents
    op.create_table('residential_incidents',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reported_by_id', sa.UUID(), nullable=False),
        sa.Column('assigned_to_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('resolution_summary', sa.Text(), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_residential_incidents_facility_id'), 'residential_incidents', ['facility_id'], unique=False)

    # residential_incident_addenda
    op.create_table('residential_incident_addenda',
        sa.Column('incident_id', sa.UUID(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('added_by', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['incident_id'], ['residential_incidents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_residential_incident_addenda_incident_id'), 'residential_incident_addenda', ['incident_id'], unique=False)

    # residential_safeguarding_records
    op.create_table('residential_safeguarding_records',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('concern_type', sa.String(length=100), nullable=False),
        sa.Column('vulnerable_group', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('reported_by_id', sa.UUID(), nullable=False),
        sa.Column('escalation_level', sa.String(length=50), nullable=False),
        sa.Column('escalated_to', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('follow_up_action', sa.Text(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_residential_safeguarding_records_client_id'), 'residential_safeguarding_records', ['client_id'], unique=False)
    op.create_index(op.f('ix_residential_safeguarding_records_facility_id'), 'residential_safeguarding_records', ['facility_id'], unique=False)

    # residential_grievances
    op.create_table('residential_grievances',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=True),
        sa.Column('submitted_by', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('investigator_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=False),
        sa.Column('corrective_action', sa.Text(), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['investigator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_residential_grievances_client_id'), 'residential_grievances', ['client_id'], unique=False)
    op.create_index(op.f('ix_residential_grievances_facility_id'), 'residential_grievances', ['facility_id'], unique=False)

    # residential_meal_plans
    op.create_table('residential_meal_plans',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=False),
        sa.Column('diet_type', sa.String(length=100), nullable=False),
        sa.Column('allergies', sa.Text(), nullable=False),
        sa.Column('special_requirements', sa.Text(), nullable=False),
        sa.Column('prescribed_by', sa.UUID(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['prescribed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_residential_meal_plans_admission_id'), 'residential_meal_plans', ['admission_id'], unique=False)
    op.create_index(op.f('ix_residential_meal_plans_facility_id'), 'residential_meal_plans', ['facility_id'], unique=False)


def downgrade() -> None:
    op.drop_table('residential_meal_plans')
    op.drop_table('residential_grievances')
    op.drop_table('residential_safeguarding_records')
    op.drop_table('residential_incident_addenda')
    op.drop_table('residential_incidents')
    op.drop_table('residential_visitor_logs')
    op.drop_table('residential_visitors')
    op.drop_table('residential_movements')
