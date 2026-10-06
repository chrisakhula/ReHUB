"""Protect care records from deletion and immutable history from mutation."""

from alembic import op

revision = "45ec2a926701"
down_revision = "12af82d0ece9"
branch_labels = None
depends_on = None

IMMUTABLE = [
    "client_revisions",
    "intake_documents",
    "pre_admission_screenings",
    "admission_status_history",
    "assessment_instruments",
    "substance_histories",
    "instrument_assessments",
    "biopsychosocial_assessments",
    "risk_assessments",
    "treatment_plans",
    "case_assignments",
    "therapy_sessions",
    "group_attendances",
    "programme_attendances",
    "family_communications",
    "clinical_encounters",
    "clinical_note_revisions",
    "clinical_vitals",
    "nursing_notes",
    "nursing_observations",
    "clinical_toxicology_tests",
    "clinical_lab_attachments",
    "prescription_revisions",
    "medication_administrations",
    "administration_addenda",
    "pharmacy_movements",
]
MUTABLE = [
    "clients",
    "client_contacts",
    "referrals",
    "admissions",
    "episodes_of_care",
    "consents",
    "admission_property",
    "wings",
    "rooms",
    "beds",
    "bed_assignments",
    "rehab_substances",
    "group_sessions",
    "programme_activities",
    "clinical_problems",
    "clinical_allergies",
    "clinical_orders",
    "nursing_handovers",
    "clinical_lab_requests",
    "clinical_lab_results",
    "medications",
    "medication_routes",
    "prescriptions",
    "medication_doses",
    "pharmacy_suppliers",
    "drug_batches",
    "ward_stock",
]


def upgrade():
    op.execute("""CREATE FUNCTION preserve_care_history() RETURNS trigger AS $$
        BEGIN
        RAISE EXCEPTION 'Care history must be preserved; use a revision or status workflow';
        END;
        $$ LANGUAGE plpgsql""")
    for table in IMMUTABLE:
        op.execute(
            f'CREATE TRIGGER preserve_history BEFORE UPDATE OR DELETE ON "{table}" '
            "FOR EACH ROW EXECUTE FUNCTION preserve_care_history()"
        )
    for table in MUTABLE:
        op.execute(
            f'CREATE TRIGGER preserve_history BEFORE DELETE ON "{table}" '
            "FOR EACH ROW EXECUTE FUNCTION preserve_care_history()"
        )
    for table in IMMUTABLE + MUTABLE:
        op.execute(
            f'CREATE TRIGGER preserve_history_truncate BEFORE TRUNCATE ON "{table}" '
            "FOR EACH STATEMENT EXECUTE FUNCTION preserve_care_history()"
        )


def downgrade():
    for table in IMMUTABLE + MUTABLE:
        op.execute(f'DROP TRIGGER preserve_history_truncate ON "{table}"')
        op.execute(f'DROP TRIGGER preserve_history ON "{table}"')
    op.execute("DROP FUNCTION preserve_care_history()")
