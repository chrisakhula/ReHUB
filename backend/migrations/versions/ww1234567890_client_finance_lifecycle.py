"""Phase 26.6: End-to-end client finance lifecycle, documents, and exports.

Revision ID: ww1234567890
Revises: vv1234567890
Create Date: 2026-10-16 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ww1234567890"
down_revision = "vv1234567890"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = [
    ("billing.financial_assessment.create", "Create and update pre-admission financial assessments"),
    ("billing.estimate.create", "Create and edit quotations and cost estimates"),
    ("billing.estimate.issue", "Issue quotations and cost estimates to clients/payers"),
    ("billing.agreement.create", "Create and revise financial agreements"),
    ("billing.agreement.approve", "Approve and activate financial agreements"),
    ("billing.payment_plan.create", "Create and configure client payment plans"),
    ("billing.payment_plan.approve", "Approve client installment payment plans"),
    ("billing.refund.request", "Request client credit balance refunds"),
    ("billing.refund.approve", "Review, approve, and execute client refunds"),
    ("billing.discharge_clearance", "Perform discharge financial review and issue clearances"),
    ("billing.export", "Export billing and client financial ledger reports"),
    ("finance.print", "Print official financial documents and receipts"),
    ("finance.email_document", "Email financial documents and statements"),
    ("resident_funds.view", "View resident pocket money accounts and statements"),
    ("resident_funds.deposit", "Receive and record resident pocket money deposits"),
    ("resident_funds.withdraw", "Process and record resident pocket money withdrawals and purchases"),
]


def upgrade() -> None:
    # 1. billing_sponsors
    op.create_table(
        "billing_sponsors",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("reference_code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("sponsor_type", sa.String(50), server_default="FAMILY", nullable=False),
        sa.Column("contact_person", sa.String(150), server_default="", nullable=False),
        sa.Column("email", sa.String(150), server_default="", nullable=False),
        sa.Column("phone", sa.String(50), server_default="", nullable=False),
        sa.Column("billing_address", sa.Text(), server_default="", nullable=False),
        sa.Column("credit_limit", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. billing_financial_assessments
    op.create_table(
        "billing_financial_assessments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("client_id", sa.UUID(), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("reference_code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("proposed_programme", sa.String(150), nullable=False),
        sa.Column("expected_duration_days", sa.Integer(), server_default="90", nullable=False),
        sa.Column("expected_admission_date", sa.Date(), nullable=True),
        sa.Column("primary_payer_type", sa.String(50), server_default="SELF", nullable=False),
        sa.Column("primary_payer_name", sa.String(200), nullable=False),
        sa.Column("secondary_payer_type", sa.String(50), nullable=True),
        sa.Column("secondary_payer_name", sa.String(200), nullable=True),
        sa.Column("sponsor_id", sa.UUID(), sa.ForeignKey("billing_sponsors.id"), nullable=True, index=True),
        sa.Column("estimated_programme_cost", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("deposit_required", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("credit_terms", sa.String(100), server_default="30_DAYS", nullable=False),
        sa.Column("installment_preference", sa.String(100), server_default="MONTHLY", nullable=False),
        sa.Column("discount_eligibility", sa.Numeric(5, 2), server_default="0.00", nullable=False),
        sa.Column("authorization_limit", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("financial_notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. billing_financial_agreements
    op.create_table(
        "billing_financial_agreements",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("client_id", sa.UUID(), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("admission_id", sa.UUID(), sa.ForeignKey("admissions.id"), nullable=True, index=True),
        sa.Column("quotation_id", sa.UUID(), nullable=True, index=True),
        sa.Column("reference_code", sa.String(50), nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("parent_agreement_id", sa.UUID(), sa.ForeignKey("billing_financial_agreements.id"), nullable=True),
        sa.Column("revision_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("programme_name", sa.String(150), nullable=False),
        sa.Column("agreed_price", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("deposit_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("deposit_paid", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("installment_terms", sa.String(200), server_default="", nullable=False),
        sa.Column("credit_terms", sa.String(100), server_default="", nullable=False),
        sa.Column("inclusions", sa.Text(), server_default="", nullable=False),
        sa.Column("exclusions", sa.Text(), server_default="", nullable=False),
        sa.Column("refund_terms", sa.Text(), server_default="", nullable=False),
        sa.Column("approved_discount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), server_default="DRAFT", nullable=False, index=True),
        sa.Column("accepted_by_name", sa.String(150), server_default="", nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_by_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 4. billing_quotations
    op.create_table(
        "billing_quotations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("client_id", sa.UUID(), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("assessment_id", sa.UUID(), sa.ForeignKey("billing_financial_assessments.id"), nullable=True, index=True),
        sa.Column("reference_code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("status", sa.String(30), server_default="DRAFT", nullable=False, index=True),
        sa.Column("programme_name", sa.String(150), nullable=False),
        sa.Column("duration_days", sa.Integer(), server_default="90", nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("tax_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("deposit_required", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("terms_and_conditions", sa.Text(), server_default="", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("accepted_by", sa.String(150), server_default="", nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_agreement_id", sa.UUID(), sa.ForeignKey("billing_financial_agreements.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add foreign key from billing_financial_agreements.quotation_id -> billing_quotations.id
    op.create_foreign_key(
        "fk_agreements_quotation",
        "billing_financial_agreements",
        "billing_quotations",
        ["quotation_id"],
        ["id"],
    )

    # 5. billing_quotation_items
    op.create_table(
        "billing_quotation_items",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("quotation_id", sa.UUID(), sa.ForeignKey("billing_quotations.id"), nullable=False, index=True),
        sa.Column("service_id", sa.UUID(), sa.ForeignKey("billing_services.id"), nullable=True),
        sa.Column("package_id", sa.UUID(), sa.ForeignKey("billing_programme_packages.id"), nullable=True),
        sa.Column("category", sa.String(50), server_default="PROGRAMME", nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), server_default="1.00", nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0.00", nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 6. billing_package_inclusions
    op.create_table(
        "billing_package_inclusions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("package_id", sa.UUID(), sa.ForeignKey("billing_programme_packages.id"), nullable=False, index=True),
        sa.Column("service_id", sa.UUID(), sa.ForeignKey("billing_services.id"), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("classification", sa.String(30), server_default="INCLUDED", nullable=False),
        sa.Column("allowed_quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("discount_percentage", sa.Numeric(5, 2), server_default="0.00", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 7. billing_package_consumptions
    op.create_table(
        "billing_package_consumptions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("admission_id", sa.UUID(), sa.ForeignKey("admissions.id"), nullable=False, index=True),
        sa.Column("package_id", sa.UUID(), sa.ForeignKey("billing_programme_packages.id"), nullable=False, index=True),
        sa.Column("service_id", sa.UUID(), sa.ForeignKey("billing_services.id"), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("quantity_allowed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quantity_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quantity_remaining", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. billing_recurring_schedules
    op.create_table(
        "billing_recurring_schedules",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("admission_id", sa.UUID(), sa.ForeignKey("admissions.id"), nullable=False, index=True),
        sa.Column("frequency", sa.String(30), nullable=False),
        sa.Column("service_id", sa.UUID(), sa.ForeignKey("billing_services.id"), nullable=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("next_run_date", sa.Date(), nullable=False, index=True),
        sa.Column("last_run_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("source_module", sa.String(50), server_default="RECURRING", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 9. billing_invoice_payer_allocations
    op.create_table(
        "billing_invoice_payer_allocations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("invoice_id", sa.UUID(), sa.ForeignKey("billing_invoices.id"), nullable=False, index=True),
        sa.Column("payer_id", sa.UUID(), sa.ForeignKey("billing_payers.id"), nullable=True),
        sa.Column("sponsor_id", sa.UUID(), sa.ForeignKey("billing_sponsors.id"), nullable=True),
        sa.Column("allocation_type", sa.String(30), server_default="PERCENTAGE", nullable=False),
        sa.Column("percentage", sa.Numeric(5, 2), server_default="0.00", nullable=False),
        sa.Column("allocated_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("responsibility_description", sa.String(200), server_default="", nullable=False),
        sa.Column("status", sa.String(30), server_default="PENDING", nullable=False, index=True),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 10. billing_payment_plans
    op.create_table(
        "billing_payment_plans",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("client_id", sa.UUID(), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("admission_id", sa.UUID(), sa.ForeignKey("admissions.id"), nullable=True, index=True),
        sa.Column("invoice_id", sa.UUID(), sa.ForeignKey("billing_invoices.id"), nullable=True, index=True),
        sa.Column("reference_code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("number_of_installments", sa.Integer(), server_default="3", nullable=False),
        sa.Column("status", sa.String(30), server_default="DRAFT", nullable=False, index=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 11. billing_payment_plan_installments
    op.create_table(
        "billing_payment_plan_installments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("plan_id", sa.UUID(), sa.ForeignKey("billing_payment_plans.id"), nullable=False, index=True),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("status", sa.String(30), server_default="PENDING", nullable=False, index=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 12. billing_refunds modifications
    op.alter_column("billing_refunds", "payment_id", nullable=True)
    op.alter_column("billing_refunds", "processed_at", nullable=True)
    op.alter_column("billing_refunds", "processed_by", nullable=True)
    op.add_column("billing_refunds", sa.Column("reference_code", sa.String(50), nullable=True))
    op.create_index(op.f("ix_billing_refunds_reference_code"), "billing_refunds", ["reference_code"], unique=True)
    op.add_column("billing_refunds", sa.Column("client_id", sa.UUID(), sa.ForeignKey("clients.id"), nullable=True))
    op.create_index(op.f("ix_billing_refunds_client_id"), "billing_refunds", ["client_id"], unique=False)
    op.add_column("billing_refunds", sa.Column("source_type", sa.String(50), server_default="OVERPAYMENT", nullable=False))
    op.add_column("billing_refunds", sa.Column("status", sa.String(30), server_default="PENDING_APPROVAL", nullable=False))
    op.create_index(op.f("ix_billing_refunds_status"), "billing_refunds", ["status"], unique=False)
    op.add_column("billing_refunds", sa.Column("requested_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("billing_refunds", sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_refunds", sa.Column("approved_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("billing_refunds", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_refunds", sa.Column("approval_notes", sa.Text(), server_default="", nullable=False))
    op.add_column("billing_refunds", sa.Column("journal_id", sa.UUID(), sa.ForeignKey("finance_journal_entries.id"), nullable=True))

    # 13. billing_resident_fund_accounts
    op.create_table(
        "billing_resident_fund_accounts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("client_id", sa.UUID(), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("admission_id", sa.UUID(), sa.ForeignKey("admissions.id"), nullable=True, index=True),
        sa.Column("reference_code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("current_balance", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 14. billing_resident_fund_transactions
    op.create_table(
        "billing_resident_fund_transactions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("account_id", sa.UUID(), sa.ForeignKey("billing_resident_fund_accounts.id"), nullable=False, index=True),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("running_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("receipt_reference", sa.String(100), server_default="", nullable=False),
        sa.Column("payment_method", sa.String(50), server_default="CASH", nullable=False),
        sa.Column("authorized_by_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("journal_id", sa.UUID(), sa.ForeignKey("finance_journal_entries.id"), nullable=True),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 15. billing_discharge_clearances
    op.create_table(
        "billing_discharge_clearances",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("client_id", sa.UUID(), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("admission_id", sa.UUID(), sa.ForeignKey("admissions.id"), nullable=False, unique=True, index=True),
        sa.Column("reference_code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("total_charges", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("total_payments", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("total_credits", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("total_refunds", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("total_writeoffs", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("outstanding_balance", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("status", sa.String(30), server_default="PENDING", nullable=False, index=True),
        sa.Column("has_payment_plan", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("payment_plan_id", sa.UUID(), sa.ForeignKey("billing_payment_plans.id"), nullable=True),
        sa.Column("is_authorized_exception", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("exception_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("exception_approved_by_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("collection_owner", sa.String(150), server_default="", nullable=False),
        sa.Column("reviewed_by_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_by_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("clearance_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 16. billing_export_audits
    op.create_table(
        "billing_export_audits",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("export_format", sa.String(20), nullable=False),
        sa.Column("report_type", sa.String(80), nullable=False),
        sa.Column("reference_code", sa.String(100), server_default="", nullable=False),
        sa.Column("filter_parameters", sa.Text(), server_default="", nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 17. Alter billing_invoice_items to add source tracking
    op.add_column("billing_invoice_items", sa.Column("source_module", sa.String(50), nullable=True))
    op.create_index(op.f("ix_billing_invoice_items_source_module"), "billing_invoice_items", ["source_module"], unique=False)
    op.add_column("billing_invoice_items", sa.Column("source_id", sa.String(100), nullable=True))
    op.create_index(op.f("ix_billing_invoice_items_source_id"), "billing_invoice_items", ["source_id"], unique=False)
    op.add_column("billing_invoice_items", sa.Column("charge_type", sa.String(50), nullable=True))
    op.create_index(op.f("ix_billing_invoice_items_charge_type"), "billing_invoice_items", ["charge_type"], unique=False)

    # 18. Seed Phase 26.6 permissions
    conn = op.get_bind()
    for code, desc in NEW_PERMISSIONS:
        conn.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, description, created_at, updated_at)
                VALUES (gen_random_uuid(), :code, :desc, NOW(), NOW())
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"code": code, "desc": desc},
        )

    # Assign permissions to Finance Officer
    officer_codes = [
        "billing.financial_assessment.create",
        "billing.estimate.create",
        "billing.estimate.issue",
        "billing.agreement.create",
        "billing.payment_plan.create",
        "billing.refund.request",
        "billing.export",
        "finance.print",
        "finance.email_document",
        "resident_funds.view",
        "resident_funds.deposit",
        "resident_funds.withdraw",
    ]
    for code in officer_codes:
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id FROM roles r, permissions p
                WHERE r.name IN ('Finance Officer', 'Finance Manager') AND p.code = :code
                ON CONFLICT DO NOTHING
                """
            ),
            {"code": code},
        )

    # Assign manager-only approvals
    manager_codes = [
        "billing.agreement.approve",
        "billing.payment_plan.approve",
        "billing.refund.approve",
        "billing.discharge_clearance",
    ]
    for code in manager_codes:
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id FROM roles r, permissions p
                WHERE r.name = 'Finance Manager' AND p.code = :code
                ON CONFLICT DO NOTHING
                """
            ),
            {"code": code},
        )


def downgrade() -> None:
    # Downgrade in reverse order
    op.drop_index(op.f("ix_billing_invoice_items_charge_type"), table_name="billing_invoice_items")
    op.drop_column("billing_invoice_items", "charge_type")
    op.drop_index(op.f("ix_billing_invoice_items_source_id"), table_name="billing_invoice_items")
    op.drop_column("billing_invoice_items", "source_id")
    op.drop_index(op.f("ix_billing_invoice_items_source_module"), table_name="billing_invoice_items")
    op.drop_column("billing_invoice_items", "source_module")

    op.drop_table("billing_export_audits")
    op.drop_table("billing_discharge_clearances")
    op.drop_table("billing_resident_fund_transactions")
    op.drop_table("billing_resident_fund_accounts")

    op.drop_index(op.f("ix_billing_refunds_status"), table_name="billing_refunds")
    op.drop_column("billing_refunds", "journal_id")
    op.drop_column("billing_refunds", "approval_notes")
    op.drop_column("billing_refunds", "approved_at")
    op.drop_column("billing_refunds", "approved_by")
    op.drop_column("billing_refunds", "requested_at")
    op.drop_column("billing_refunds", "requested_by")
    op.drop_column("billing_refunds", "status")
    op.drop_column("billing_refunds", "source_type")
    op.drop_index(op.f("ix_billing_refunds_client_id"), table_name="billing_refunds")
    op.drop_column("billing_refunds", "client_id")
    op.drop_index(op.f("ix_billing_refunds_reference_code"), table_name="billing_refunds")
    op.drop_column("billing_refunds", "reference_code")

    op.drop_table("billing_payment_plan_installments")
    op.drop_table("billing_payment_plans")
    op.drop_table("billing_invoice_payer_allocations")
    op.drop_table("billing_recurring_schedules")
    op.drop_table("billing_package_consumptions")
    op.drop_table("billing_package_inclusions")
    op.drop_table("billing_quotation_items")

    op.drop_constraint("fk_agreements_quotation", "billing_financial_agreements", type_="foreignkey")
    op.drop_table("billing_quotations")
    op.drop_table("billing_financial_agreements")
    op.drop_table("billing_financial_assessments")
    op.drop_table("billing_sponsors")
