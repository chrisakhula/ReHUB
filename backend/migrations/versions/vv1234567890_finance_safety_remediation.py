"""Phase 26.5: Finance safety, accounting integrity, and control remediation.

Revision ID: vv1234567890
Revises: uu6789012345
Create Date: 2026-10-16 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "vv1234567890"
down_revision = "uu6789012345"
branch_labels = None
depends_on = None


NEW_PERMISSIONS = [
    ("billing.issue", "Issue draft invoices to client"),
    ("billing.credit_note.create", "Request or create credit note for invoice adjustment"),
    ("billing.credit_note.approve", "Approve and post credit notes"),
    ("billing.writeoff.request", "Request invoice bad debt write-off"),
    ("billing.writeoff.approve", "Approve and post invoice bad debt write-off"),
    ("finance.audit", "View accounting integrity diagnostics and reconciliation logs"),
    ("finance.reopen_period", "Reopen locked or closed fiscal periods"),
]


def upgrade() -> None:
    # 1. Alter billing_credit_notes
    op.add_column("billing_credit_notes", sa.Column("reason_code", sa.String(50), server_default="OTHER", nullable=False))
    op.add_column("billing_credit_notes", sa.Column("requested_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("billing_credit_notes", sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_credit_notes", sa.Column("approved_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("billing_credit_notes", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_credit_notes", sa.Column("approval_notes", sa.Text(), server_default="", nullable=False))
    op.add_column("billing_credit_notes", sa.Column("journal_id", sa.UUID(), sa.ForeignKey("finance_journal_entries.id"), nullable=True))
    op.create_index(op.f("ix_billing_credit_notes_status"), "billing_credit_notes", ["status"], unique=False)

    # 2. Alter billing_write_offs
    op.alter_column("billing_write_offs", "approved_by", nullable=True)
    op.alter_column("billing_write_offs", "written_off_at", nullable=True)
    op.add_column("billing_write_offs", sa.Column("reference_code", sa.String(50), nullable=True))
    op.create_index(op.f("ix_billing_write_offs_reference_code"), "billing_write_offs", ["reference_code"], unique=True)
    op.add_column("billing_write_offs", sa.Column("status", sa.String(30), server_default="POSTED", nullable=False))
    op.create_index(op.f("ix_billing_write_offs_status"), "billing_write_offs", ["status"], unique=False)
    op.add_column("billing_write_offs", sa.Column("requested_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("billing_write_offs", sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_write_offs", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_write_offs", sa.Column("approval_notes", sa.Text(), server_default="", nullable=False))
    op.add_column("billing_write_offs", sa.Column("journal_id", sa.UUID(), sa.ForeignKey("finance_journal_entries.id"), nullable=True))

    # Safe backfill for historical write-offs
    op.execute("""
        UPDATE billing_write_offs
        SET requested_by = approved_by,
            requested_at = written_off_at,
            approved_at = written_off_at,
            reference_code = 'WO-HIST-' || substring(id::text from 1 for 8)
        WHERE reference_code IS NULL
    """)

    # 3. Alter finance_cash_reconciliations
    op.add_column("finance_cash_reconciliations", sa.Column("reference_code", sa.String(50), nullable=True))
    op.create_index(op.f("ix_finance_cash_reconciliations_reference_code"), "finance_cash_reconciliations", ["reference_code"], unique=True)
    op.add_column("finance_cash_reconciliations", sa.Column("cashier_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("finance_cash_reconciliations", sa.Column("variance_type", sa.String(20), nullable=True))
    op.add_column("finance_cash_reconciliations", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("finance_cash_reconciliations", sa.Column("review_notes", sa.Text(), server_default="", nullable=False))
    op.add_column("finance_cash_reconciliations", sa.Column("approved_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("finance_cash_reconciliations", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("finance_cash_reconciliations", sa.Column("journal_id", sa.UUID(), sa.ForeignKey("finance_journal_entries.id"), nullable=True))

    # Safe backfill for cash reconciliations
    op.execute("""
        UPDATE finance_cash_reconciliations
        SET reference_code = 'CRN-HIST-' || substring(id::text from 1 for 8),
            variance_type = CASE WHEN variance < 0 THEN 'SHORTAGE' WHEN variance > 0 THEN 'OVERAGE' ELSE 'BALANCED' END
        WHERE reference_code IS NULL
    """)

    # 4. Permissions & RBAC remediation
    now = "NOW()"
    for code, desc in NEW_PERMISSIONS:
        op.execute(f"""
            INSERT INTO permissions (id, code, description, created_at, updated_at)
            VALUES (gen_random_uuid(), '{code}', '{desc}', {now}, {now})
            ON CONFLICT (code) DO NOTHING
        """)

    # Ensure Finance Manager role exists
    op.execute("""
        INSERT INTO roles (id, name, description, created_at, updated_at)
        VALUES (gen_random_uuid(), 'Finance Manager', 'Senior financial controller and accounting authorizations', NOW(), NOW())
        ON CONFLICT (name) DO NOTHING
    """)

    # Revoke business approval and configuration permissions from ICT / System Administrator and Super Administrator
    op.execute("""
        DELETE FROM role_permissions
        WHERE role_id IN (SELECT id FROM roles WHERE name IN ('System Administrator', 'Super Administrator'))
          AND permission_id IN (
              SELECT id FROM permissions WHERE code IN (
                  'finance.approve',
                  'finance.configure',
                  'finance.close_period',
                  'finance.reopen_period',
                  'finance.edit',
                  'billing.credit_note.approve',
                  'billing.writeoff.approve'
              )
          )
    """)

    # Assign operational creation to Finance Officer
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Finance Officer'
          AND p.code IN (
              'billing.issue',
              'billing.credit_note.create',
              'billing.writeoff.request',
              'finance.audit'
          )
        ON CONFLICT DO NOTHING
    """)

    # Assign senior approvals to Finance Manager and Facility Administrator
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Finance Manager', 'Facility Administrator')
          AND p.code IN (
              'billing.credit_note.approve',
              'billing.writeoff.approve',
              'finance.approve',
              'finance.configure',
              'finance.close_period',
              'finance.reopen_period',
              'finance.audit',
              'finance.view',
              'billing.view'
          )
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # Reverse RBAC assignments
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE code IN (
                'billing.issue',
                'billing.credit_note.create',
                'billing.credit_note.approve',
                'billing.writeoff.request',
                'billing.writeoff.approve',
                'finance.audit',
                'finance.reopen_period'
            )
        )
    """)
    op.execute("""
        DELETE FROM permissions
        WHERE code IN (
            'billing.issue',
            'billing.credit_note.create',
            'billing.credit_note.approve',
            'billing.writeoff.request',
            'billing.writeoff.approve',
            'finance.audit',
            'finance.reopen_period'
        )
    """)

    # Drop columns
    op.drop_column("finance_cash_reconciliations", "journal_id")
    op.drop_column("finance_cash_reconciliations", "approved_at")
    op.drop_column("finance_cash_reconciliations", "approved_by")
    op.drop_column("finance_cash_reconciliations", "review_notes")
    op.drop_column("finance_cash_reconciliations", "reviewed_at")
    op.drop_column("finance_cash_reconciliations", "variance_type")
    op.drop_column("finance_cash_reconciliations", "cashier_id")
    op.drop_index(op.f("ix_finance_cash_reconciliations_reference_code"), table_name="finance_cash_reconciliations")
    op.drop_column("finance_cash_reconciliations", "reference_code")

    op.drop_column("billing_write_offs", "journal_id")
    op.drop_column("billing_write_offs", "approval_notes")
    op.drop_column("billing_write_offs", "approved_at")
    op.drop_column("billing_write_offs", "requested_at")
    op.drop_column("billing_write_offs", "requested_by")
    op.drop_index(op.f("ix_billing_write_offs_status"), table_name="billing_write_offs")
    op.drop_column("billing_write_offs", "status")
    op.drop_index(op.f("ix_billing_write_offs_reference_code"), table_name="billing_write_offs")
    op.drop_column("billing_write_offs", "reference_code")
    op.alter_column("billing_write_offs", "written_off_at", nullable=False)
    op.alter_column("billing_write_offs", "approved_by", nullable=False)

    op.drop_index(op.f("ix_billing_credit_notes_status"), table_name="billing_credit_notes")
    op.drop_column("billing_credit_notes", "journal_id")
    op.drop_column("billing_credit_notes", "approval_notes")
    op.drop_column("billing_credit_notes", "approved_at")
    op.drop_column("billing_credit_notes", "approved_by")
    op.drop_column("billing_credit_notes", "requested_at")
    op.drop_column("billing_credit_notes", "requested_by")
    op.drop_column("billing_credit_notes", "reason_code")
