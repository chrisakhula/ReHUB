"""General ledger, payables, expenses, and reconciliation models."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.identity import Record


class FinanceAccount(Record, Base):
    __tablename__ = "finance_accounts"
    __table_args__ = (
        UniqueConstraint("facility_id", "code", name="uq_finance_account_code"),
    )

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    code: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(30), index=True)
    normal_balance: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    system_account: Mapped[bool] = mapped_column(Boolean, default=False)

    lines: Mapped[list["FinanceJournalLine"]] = relationship(back_populates="account")


class FinanceFiscalPeriod(Record, Base):
    __tablename__ = "finance_fiscal_periods"
    __table_args__ = (
        UniqueConstraint("facility_id", "name", name="uq_finance_fiscal_period_name"),
    )

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    locked_by: Mapped[UUID | None] = mapped_column(Uuid)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[UUID | None] = mapped_column(Uuid)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="")


class FinanceJournalEntry(Record, Base):
    __tablename__ = "finance_journal_entries"

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    reference: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text)
    source_module: Mapped[str] = mapped_column(String(80), index=True)
    source_id: Mapped[str | None] = mapped_column(String(120), index=True)
    posting_type: Mapped[str] = mapped_column(String(80), default="MANUAL", index=True)
    status: Mapped[str] = mapped_column(String(20), default="POSTED", index=True)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversed_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("finance_journal_entries.id")
    )

    lines: Mapped[list["FinanceJournalLine"]] = relationship(
        back_populates="journal_entry", cascade="all, delete-orphan"
    )


class FinanceJournalLine(Record, Base):
    __tablename__ = "finance_journal_lines"

    journal_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance_journal_entries.id"), index=True
    )
    account_id: Mapped[UUID] = mapped_column(ForeignKey("finance_accounts.id"), index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    description: Mapped[str] = mapped_column(Text, default="")

    journal_entry: Mapped[FinanceJournalEntry] = relationship(back_populates="lines")
    account: Mapped[FinanceAccount] = relationship(back_populates="lines")


class FinanceExpenseCategory(Record, Base):
    __tablename__ = "finance_expense_categories"
    __table_args__ = (
        UniqueConstraint("facility_id", "name", name="uq_finance_expense_category"),
    )

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    account_id: Mapped[UUID] = mapped_column(ForeignKey("finance_accounts.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FinanceExpenseVoucher(Record, Base):
    __tablename__ = "finance_expense_vouchers"

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    expense_category_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance_expense_categories.id")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_method: Mapped[str] = mapped_column(String(50))
    payment_account_id: Mapped[UUID | None] = mapped_column(ForeignKey("finance_accounts.id"))
    paid_to: Mapped[str] = mapped_column(String(200))
    reference: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    expense_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinanceSupplier(Record, Base):
    __tablename__ = "finance_suppliers"
    __table_args__ = (
        UniqueConstraint("facility_id", "name", name="uq_finance_supplier_name"),
    )

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    contact_person: Mapped[str] = mapped_column(String(150), default="")
    email: Mapped[str] = mapped_column(String(150), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    tax_pin: Mapped[str] = mapped_column(String(50), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FinanceSupplierInvoice(Record, Base):
    __tablename__ = "finance_supplier_invoices"
    __table_args__ = (
        UniqueConstraint(
            "facility_id",
            "supplier_id",
            "invoice_number",
            name="uq_finance_supplier_invoice",
        ),
    )

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("finance_suppliers.id"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), index=True)
    invoice_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    invoice_type: Mapped[str] = mapped_column(String(30), default="DIRECT_EXPENSE")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED", index=True)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="")

    items: Mapped[list["FinanceSupplierInvoiceItem"]] = relationship(
        cascade="all, delete-orphan"
    )


class FinanceSupplierInvoiceItem(Record, Base):
    __tablename__ = "finance_supplier_invoice_items"

    supplier_invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance_supplier_invoices.id"), index=True
    )
    account_id: Mapped[UUID] = mapped_column(ForeignKey("finance_accounts.id"))
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)


class FinanceSupplierPayment(Record, Base):
    __tablename__ = "finance_supplier_payments"

    supplier_invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance_supplier_invoices.id"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_method: Mapped[str] = mapped_column(String(50))
    payment_account_id: Mapped[UUID] = mapped_column(ForeignKey("finance_accounts.id"))
    payment_reference: Mapped[str] = mapped_column(String(120), default="")
    payment_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")


class FinanceCashReconciliation(Record, Base):
    __tablename__ = "finance_cash_reconciliations"

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    period_date: Mapped[date] = mapped_column(Date, index=True)
    cashier_name: Mapped[str] = mapped_column(String(150), default="")
    opening_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    expected_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    counted_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    variance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="POSTED", index=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(Uuid)
    notes: Mapped[str] = mapped_column(Text, default="")


class FinancePaymentReconciliation(Record, Base):
    __tablename__ = "finance_payment_reconciliations"

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    method: Mapped[str] = mapped_column(String(50), index=True)
    period_date: Mapped[date] = mapped_column(Date, index=True)
    system_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    statement_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    variance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    missing_references: Mapped[str] = mapped_column(Text, default="")
    duplicate_references: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    checked_by: Mapped[UUID | None] = mapped_column(Uuid)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid)
