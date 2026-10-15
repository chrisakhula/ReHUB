"""Add high-volume performance indexes for institutional search and filtering

Revision ID: qq2345678901
Revises: pp1234567890
"""

import sqlalchemy as sa
from alembic import op

revision = "qq2345678901"
down_revision = "pp1234567890"
branch_labels = None
depends_on = None


def upgrade():
    # Helper to safely create index if not existing
    conn = op.get_bind()

    indexes = [
        # Table, index_name, columns
        ("clients", "ix_clients_client_number_perf", ["client_number"]),
        ("clients", "ix_clients_national_id_perf", ["national_id"]),
        ("clients", "ix_clients_facility_id_perf", ["facility_id"]),
        ("admissions", "ix_admissions_admission_number_perf", ["admission_number"]),
        ("admissions", "ix_admissions_status_perf", ["status"]),
        ("billing_invoices", "ix_invoices_invoice_number_perf", ["invoice_number"]),
        ("billing_invoices", "ix_invoices_status_perf", ["status"]),
        ("billing_invoices", "ix_invoices_facility_id_perf", ["facility_id"]),
        ("billing_payments", "ix_payments_reference_perf", ["transaction_reference"]),
        ("billing_payments", "ix_payments_facility_id_perf", ["facility_id"]),
        ("billing_mpesa_transactions", "ix_mpesa_receipt_perf", ["transaction_reference"]),
        ("billing_mpesa_transactions", "ix_mpesa_status_perf", ["status"]),
        ("clinical_crisis_alerts", "ix_crisis_alerts_status_perf", ["status"]),
        ("clinical_crisis_alerts", "ix_crisis_alerts_severity_perf", ["severity"]),
        ("audit_events", "ix_audit_events_facility_action_perf", ["facility_id", "action"]),
        ("data_subject_requests", "ix_dsar_facility_status_perf", ["facility_id", "status"]),
        ("data_breaches", "ix_breaches_facility_status_perf", ["facility_id", "status"]),
        ("export_requests", "ix_exports_facility_status_perf", ["facility_id", "status"]),
    ]

    for table, name, cols in indexes:
        # Check if index already exists in postgres
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM pg_indexes WHERE indexname = :name"
            ).bindparams(name=name)
        ).scalar()
        if not result:
            op.create_index(name, table, cols)


def downgrade():
    indexes = [
        ("clients", "ix_clients_client_number_perf"),
        ("clients", "ix_clients_national_id_perf"),
        ("clients", "ix_clients_facility_id_perf"),
        ("admissions", "ix_admissions_admission_number_perf"),
        ("admissions", "ix_admissions_status_perf"),
        ("billing_invoices", "ix_invoices_invoice_number_perf"),
        ("billing_invoices", "ix_invoices_status_perf"),
        ("billing_invoices", "ix_invoices_facility_id_perf"),
        ("billing_payments", "ix_payments_reference_perf"),
        ("billing_payments", "ix_payments_facility_id_perf"),
        ("billing_mpesa_transactions", "ix_mpesa_receipt_perf"),
        ("billing_mpesa_transactions", "ix_mpesa_status_perf"),
        ("clinical_crisis_alerts", "ix_crisis_alerts_status_perf"),
        ("clinical_crisis_alerts", "ix_crisis_alerts_severity_perf"),
        ("audit_events", "ix_audit_events_facility_action_perf"),
        ("data_subject_requests", "ix_dsar_facility_status_perf"),
        ("data_breaches", "ix_breaches_facility_status_perf"),
        ("export_requests", "ix_exports_facility_status_perf"),
    ]
    for table, name in indexes:
        op.drop_index(name, table_name=table)
