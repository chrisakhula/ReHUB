"""Finance ledger foundation

Revision ID: kk6789012345
Revises: 274c7a9e6ac8
"""

from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "kk6789012345"
down_revision = "274c7a9e6ac8"
branch_labels = None
depends_on = None

FINANCE_PERMISSIONS = [
    ("b0c84788-cc77-45c4-94e4-b9748a706101", "finance.view", "View finance records"),
    ("b0c84788-cc77-45c4-94e4-b9748a706102", "finance.edit", "Create finance records"),
    ("b0c84788-cc77-45c4-94e4-b9748a706103", "finance.approve", "Approve finance records"),
    ("b0c84788-cc77-45c4-94e4-b9748a706104", "finance.reports", "View finance reports"),
    ("b0c84788-cc77-45c4-94e4-b9748a706105", "finance.configure", "Configure finance setup"),
]


def record_columns():
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    ]


def upgrade():
    op.create_table(
        "finance_accounts",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("normal_balance", sa.String(length=10), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("system_account", sa.Boolean(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_id", "code", name="uq_finance_account_code"),
    )
    op.create_index("ix_finance_accounts_facility_id", "finance_accounts", ["facility_id"])
    op.create_index("ix_finance_accounts_code", "finance_accounts", ["code"])
    op.create_index("ix_finance_accounts_type", "finance_accounts", ["type"])

    op.create_table(
        "finance_fiscal_periods",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("locked_by", sa.Uuid(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.Uuid(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_id", "name", name="uq_finance_fiscal_period_name"),
    )
    op.create_index(
        "ix_finance_fiscal_periods_facility_id",
        "finance_fiscal_periods",
        ["facility_id"],
    )
    op.create_index("ix_finance_fiscal_periods_status", "finance_fiscal_periods", ["status"])

    op.create_table(
        "finance_journal_entries",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_module", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=True),
        sa.Column("posting_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_entry_id", sa.Uuid(), nullable=True),
        *record_columns(),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["reversed_entry_id"], ["finance_journal_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_journal_entries_facility_id",
        "finance_journal_entries",
        ["facility_id"],
    )
    op.create_index("ix_finance_journal_entries_entry_date", "finance_journal_entries", ["entry_date"])
    op.create_index("ix_finance_journal_entries_reference", "finance_journal_entries", ["reference"])
    op.create_index(
        "ix_finance_journal_entries_source_module",
        "finance_journal_entries",
        ["source_module"],
    )
    op.create_index("ix_finance_journal_entries_source_id", "finance_journal_entries", ["source_id"])
    op.create_index(
        "ix_finance_journal_entries_posting_type",
        "finance_journal_entries",
        ["posting_type"],
    )
    op.create_index("ix_finance_journal_entries_status", "finance_journal_entries", ["status"])

    op.create_table(
        "finance_journal_lines",
        sa.Column("journal_entry_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("debit", sa.Numeric(14, 2), nullable=False),
        sa.Column("credit", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["account_id"], ["finance_accounts.id"]),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["finance_journal_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_journal_lines_journal_entry_id",
        "finance_journal_lines",
        ["journal_entry_id"],
    )
    op.create_index("ix_finance_journal_lines_account_id", "finance_journal_lines", ["account_id"])

    op.create_table(
        "finance_expense_categories",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["account_id"], ["finance_accounts.id"]),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_id", "name", name="uq_finance_expense_category"),
    )
    op.create_index(
        "ix_finance_expense_categories_facility_id",
        "finance_expense_categories",
        ["facility_id"],
    )

    op.create_table(
        "finance_expense_vouchers",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("expense_category_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=50), nullable=False),
        sa.Column("payment_account_id", sa.Uuid(), nullable=True),
        sa.Column("paid_to", sa.String(length=200), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *record_columns(),
        sa.ForeignKeyConstraint(["expense_category_id"], ["finance_expense_categories.id"]),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["payment_account_id"], ["finance_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_expense_vouchers_facility_id",
        "finance_expense_vouchers",
        ["facility_id"],
    )
    op.create_index("ix_finance_expense_vouchers_status", "finance_expense_vouchers", ["status"])

    op.create_table(
        "finance_suppliers",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("contact_person", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("tax_pin", sa.String(length=50), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_id", "name", name="uq_finance_supplier_name"),
    )
    op.create_index("ix_finance_suppliers_facility_id", "finance_suppliers", ["facility_id"])

    op.create_table(
        "finance_supplier_invoices",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_number", sa.String(length=100), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("invoice_type", sa.String(length=30), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["finance_suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "facility_id",
            "supplier_id",
            "invoice_number",
            name="uq_finance_supplier_invoice",
        ),
    )
    op.create_index(
        "ix_finance_supplier_invoices_facility_id",
        "finance_supplier_invoices",
        ["facility_id"],
    )
    op.create_index(
        "ix_finance_supplier_invoices_supplier_id",
        "finance_supplier_invoices",
        ["supplier_id"],
    )
    op.create_index(
        "ix_finance_supplier_invoices_invoice_number",
        "finance_supplier_invoices",
        ["invoice_number"],
    )
    op.create_index("ix_finance_supplier_invoices_status", "finance_supplier_invoices", ["status"])

    op.create_table(
        "finance_supplier_invoice_items",
        sa.Column("supplier_invoice_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["account_id"], ["finance_accounts.id"]),
        sa.ForeignKeyConstraint(["supplier_invoice_id"], ["finance_supplier_invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_supplier_invoice_items_supplier_invoice_id",
        "finance_supplier_invoice_items",
        ["supplier_invoice_id"],
    )

    op.create_table(
        "finance_supplier_payments",
        sa.Column("supplier_invoice_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=50), nullable=False),
        sa.Column("payment_account_id", sa.Uuid(), nullable=False),
        sa.Column("payment_reference", sa.String(length=120), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["payment_account_id"], ["finance_accounts.id"]),
        sa.ForeignKeyConstraint(["supplier_invoice_id"], ["finance_supplier_invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_supplier_payments_supplier_invoice_id",
        "finance_supplier_payments",
        ["supplier_invoice_id"],
    )

    op.create_table(
        "finance_cash_reconciliations",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("cashier_name", sa.String(length=150), nullable=False),
        sa.Column("opening_cash", sa.Numeric(14, 2), nullable=False),
        sa.Column("expected_cash", sa.Numeric(14, 2), nullable=False),
        sa.Column("counted_cash", sa.Numeric(14, 2), nullable=False),
        sa.Column("variance", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_cash_reconciliations_facility_id",
        "finance_cash_reconciliations",
        ["facility_id"],
    )
    op.create_index(
        "ix_finance_cash_reconciliations_period_date",
        "finance_cash_reconciliations",
        ["period_date"],
    )
    op.create_index("ix_finance_cash_reconciliations_status", "finance_cash_reconciliations", ["status"])

    op.create_table(
        "finance_payment_reconciliations",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("system_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("statement_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("variance", sa.Numeric(14, 2), nullable=False),
        sa.Column("missing_references", sa.Text(), nullable=False),
        sa.Column("duplicate_references", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("checked_by", sa.Uuid(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        *record_columns(),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_payment_reconciliations_facility_id",
        "finance_payment_reconciliations",
        ["facility_id"],
    )
    op.create_index(
        "ix_finance_payment_reconciliations_method",
        "finance_payment_reconciliations",
        ["method"],
    )
    op.create_index(
        "ix_finance_payment_reconciliations_period_date",
        "finance_payment_reconciliations",
        ["period_date"],
    )
    op.create_index(
        "ix_finance_payment_reconciliations_status",
        "finance_payment_reconciliations",
        ["status"],
    )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("created_by", sa.Uuid()),
        sa.column("updated_by", sa.Uuid()),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        permissions,
        [
            {
                "id": UUID(permission_id),
                "code": code,
                "description": description,
                "created_at": now,
                "updated_at": now,
                "created_by": None,
                "updated_by": None,
            }
            for permission_id, code, description in FINANCE_PERMISSIONS
        ],
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT roles.id, permissions.id
        FROM roles
        CROSS JOIN permissions
        WHERE roles.name IN ('Super Administrator', 'System Administrator', 'Facility Administrator')
          AND permissions.code IN (
            'finance.view',
            'finance.edit',
            'finance.approve',
            'finance.reports',
            'finance.configure'
          )
        ON CONFLICT DO NOTHING
        """
    )


def downgrade():
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
          SELECT id FROM permissions WHERE code LIKE 'finance.%'
        )
        """
    )
    op.execute("DELETE FROM permissions WHERE code LIKE 'finance.%'")
    op.drop_table("finance_payment_reconciliations")
    op.drop_table("finance_cash_reconciliations")
    op.drop_table("finance_supplier_payments")
    op.drop_table("finance_supplier_invoice_items")
    op.drop_table("finance_supplier_invoices")
    op.drop_table("finance_suppliers")
    op.drop_table("finance_expense_vouchers")
    op.drop_table("finance_expense_categories")
    op.drop_table("finance_journal_lines")
    op.drop_table("finance_journal_entries")
    op.drop_table("finance_fiscal_periods")
    op.drop_table("finance_accounts")
