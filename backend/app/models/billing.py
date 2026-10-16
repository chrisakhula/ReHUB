"""Billing, payments, and financial management models."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class BillingService(Record, Base):
    __tablename__ = "billing_services"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100)) # e.g. CONSULTATION, ACCOMMODATION, MEDICATION
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ProgrammePackage(Record, Base):
    __tablename__ = "billing_programme_packages"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    duration_days: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceList(Record, Base):
    __tablename__ = "billing_price_lists"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_services.id"), nullable=True)
    package_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_programme_packages.id"), nullable=True)
    payer_category: Mapped[str] = mapped_column(String(50), default="DEFAULT") # e.g. INSURANCE, PRIVATE
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Payer(Record, Base):
    __tablename__ = "billing_payers"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    payer_type: Mapped[str] = mapped_column(String(50)) # e.g. INSURANCE, PRIVATE, CORPORATE, SPONSOR
    contact_person: Mapped[str] = mapped_column(String(150), default="")
    contact_email: Mapped[str] = mapped_column(String(150), default="")
    contact_phone: Mapped[str] = mapped_column(String(50), default="")
    billing_address: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ClientPayerRelationship(Record, Base):
    __tablename__ = "billing_client_payers"
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("billing_payers.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(50)) # e.g. PRIMARY, SECONDARY, SELF
    policy_number: Mapped[str] = mapped_column(String(100), default="")
    coverage_details: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Invoice(Record, Base):
    __tablename__ = "billing_invoices"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey("admissions.id"), index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_payers.id"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT") # DRAFT, ISSUED, PARTIAL, PAID, CANCELLED, WRITTEN_OFF
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    notes: Mapped[str] = mapped_column(Text, default="")


class InvoiceItem(Record, Base):
    __tablename__ = "billing_invoice_items"
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), index=True)
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_services.id"))
    package_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_programme_packages.id"))
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1.00"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Payment(Record, Base):
    __tablename__ = "billing_payments"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_payers.id"), index=True)
    client_id: Mapped[UUID | None] = mapped_column(ForeignKey("clients.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str] = mapped_column(String(50)) # CASH, MPESA, CARD, TRANSFER
    transaction_reference: Mapped[str] = mapped_column(String(100), index=True)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED") # PENDING, COMPLETED, FAILED, REFUNDED
    notes: Mapped[str] = mapped_column(Text, default="")


class PaymentAllocation(Record, Base):
    __tablename__ = "billing_payment_allocations"
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("billing_payments.id"), index=True)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    allocated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class Receipt(Record, Base):
    __tablename__ = "billing_receipts"
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("billing_payments.id"), index=True)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str] = mapped_column(Text, default="")


class CreditNote(Record, Base):
    __tablename__ = "billing_credit_notes"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), index=True)
    credit_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason_code: Mapped[str] = mapped_column(String(50), default="OTHER") # BILLING_ERROR, DUPLICATE_CHARGE, SERVICE_NOT_DELIVERED, APPROVED_DISCOUNT, EARLY_DISCHARGE_ADJUSTMENT, OTHER
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_APPROVAL", index=True) # DRAFT, PENDING_APPROVAL, APPROVED, REJECTED, POSTED, CANCELLED
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    requested_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[str] = mapped_column(Text, default="")
    journal_id: Mapped[UUID | None] = mapped_column(ForeignKey("finance_journal_entries.id"), nullable=True)


class Refund(Record, Base):
    __tablename__ = "billing_refunds"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("billing_payments.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text)
    refund_method: Mapped[str] = mapped_column(String(50))
    transaction_reference: Mapped[str] = mapped_column(String(100), default="")
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class WriteOff(Record, Base):
    __tablename__ = "billing_write_offs"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), index=True)
    reference_code: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_APPROVAL", index=True) # PENDING_APPROVAL, APPROVED, REJECTED, POSTED
    requested_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    written_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[str] = mapped_column(Text, default="")
    journal_id: Mapped[UUID | None] = mapped_column(ForeignKey("finance_journal_entries.id"), nullable=True)


class Adjustment(Record, Base):
    __tablename__ = "billing_adjustments"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2)) # Can be positive or negative
    reason: Mapped[str] = mapped_column(Text)
    adjustment_type: Mapped[str] = mapped_column(String(50)) # DISCOUNT, PENALTY, CORRECTION
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class MpesaTransaction(Record, Base):
    __tablename__ = "billing_mpesa_transactions"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    transaction_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_payers.id"), nullable=True)
    client_id: Mapped[UUID | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    invoice_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_invoices.id"), nullable=True, index=True)
    merchant_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    checkout_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    response_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="CREATED", index=True)  # CREATED, REQUESTED, PENDING, SUCCESS, FAILED, TIMEOUT, CANCELLED, RECONCILED
    reconciliation_status: Mapped[str] = mapped_column(String(30), default="UNMATCHED", index=True)  # AUTO_RECONCILED, MANUAL_REVIEW, UNMATCHED, DUPLICATE, FAILED, REVERSED
    reconciled_payment_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_payments.id"), nullable=True)
    reconciled_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciliation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text, default="")
