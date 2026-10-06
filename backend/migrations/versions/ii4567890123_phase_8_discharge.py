"""phase_8_discharge

Revision ID: ii4567890123
Revises: hh3456789012
Create Date: 2026-10-06 11:27:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ii4567890123'
down_revision = 'hh3456789012'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Drop old tables if they exist
    op.execute("DROP TABLE IF EXISTS aftercare_contacts CASCADE")
    op.execute("DROP TABLE IF EXISTS aftercare_cases CASCADE")
    op.execute("DROP TABLE IF EXISTS discharge_plans CASCADE")

    # discharge_plans
    op.create_table('discharge_plans',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=False),
        sa.Column('goals_achieved', sa.Text(), nullable=False),
        sa.Column('unresolved_risks', sa.Text(), nullable=False),
        sa.Column('relapse_prevention', sa.Text(), nullable=False),
        sa.Column('accommodation', sa.String(length=200), nullable=False),
        sa.Column('family_support', sa.String(length=200), nullable=False),
        sa.Column('work_education', sa.String(length=200), nullable=False),
        sa.Column('support_groups', sa.Text(), nullable=False),
        sa.Column('appointments', sa.Text(), nullable=False),
        sa.Column('referrals', sa.Text(), nullable=False),
        sa.Column('emergency_plans', sa.Text(), nullable=False),
        sa.Column('medication_instructions', sa.Text(), nullable=False),
        sa.Column('belongings_returned', sa.Boolean(), nullable=False),
        sa.Column('discharge_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('discharge_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('responsible_staff_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['responsible_staff_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discharge_plans_admission_id'), 'discharge_plans', ['admission_id'], unique=False)
    op.create_index(op.f('ix_discharge_plans_facility_id'), 'discharge_plans', ['facility_id'], unique=False)

    # discharge_aftercare_cases
    op.create_table('discharge_aftercare_cases',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=True),
        sa.Column('assigned_staff_id', sa.UUID(), nullable=False),
        sa.Column('follow_up_intervals', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['assigned_staff_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discharge_aftercare_cases_client_id'), 'discharge_aftercare_cases', ['client_id'], unique=False)
    op.create_index(op.f('ix_discharge_aftercare_cases_facility_id'), 'discharge_aftercare_cases', ['facility_id'], unique=False)

    # discharge_aftercare_contacts
    op.create_table('discharge_aftercare_contacts',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('staff_id', sa.UUID(), nullable=False),
        sa.Column('contact_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('successful', sa.Boolean(), nullable=False),
        sa.Column('abstinence', sa.Boolean(), nullable=False),
        sa.Column('support_participation', sa.String(length=100), nullable=False),
        sa.Column('employment_education', sa.String(length=100), nullable=False),
        sa.Column('housing', sa.String(length=100), nullable=False),
        sa.Column('family_relations', sa.String(length=100), nullable=False),
        sa.Column('medication_adherence', sa.String(length=100), nullable=False),
        sa.Column('wellbeing', sa.String(length=100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('referrals_made', sa.Text(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['discharge_aftercare_cases.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['staff_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discharge_aftercare_contacts_case_id'), 'discharge_aftercare_contacts', ['case_id'], unique=False)
    op.create_index(op.f('ix_discharge_aftercare_contacts_facility_id'), 'discharge_aftercare_contacts', ['facility_id'], unique=False)

    # discharge_relapse_records
    op.create_table('discharge_relapse_records',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=True),
        sa.Column('reported_by_id', sa.UUID(), nullable=False),
        sa.Column('substance', sa.String(length=200), nullable=False),
        sa.Column('date_of_relapse', sa.DateTime(timezone=True), nullable=False),
        sa.Column('triggers', sa.Text(), nullable=False),
        sa.Column('circumstances', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('consequences', sa.Text(), nullable=False),
        sa.Column('protective_factors', sa.Text(), nullable=False),
        sa.Column('intervention', sa.Text(), nullable=False),
        sa.Column('clinical_review', sa.Text(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['discharge_aftercare_cases.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discharge_relapse_records_client_id'), 'discharge_relapse_records', ['client_id'], unique=False)
    op.create_index(op.f('ix_discharge_relapse_records_facility_id'), 'discharge_relapse_records', ['facility_id'], unique=False)


def downgrade() -> None:
    op.drop_table('discharge_relapse_records')
    op.drop_table('discharge_aftercare_contacts')
    op.drop_table('discharge_aftercare_cases')
    op.drop_table('discharge_plans')
