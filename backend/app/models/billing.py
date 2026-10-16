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
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_services.id"), nullable=True)
    package_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_programme_packages.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1.00"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    source_module: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    charge_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)


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
    reference_code: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    client_id: Mapped[UUID | None] = mapped_column(ForeignKey("clients.id"), index=True, nullable=True)
    payment_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_payments.id"), index=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), default="OVERPAYMENT") # CLIENT_DEPOSIT, REVENUE_ADJUSTMENT, OVERPAYMENT
    refund_method: Mapped[str] = mapped_column(String(50))
    transaction_reference: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(30), default="PENDING_APPROVAL", index=True) # DRAFT, PENDING_APPROVAL, APPROVED, PAID, REJECTED, CANCELLED
    requested_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[str] = mapped_column(Text, default="")
    journal_id: Mapped[UUID | None] = mapped_column(ForeignKey("finance_journal_entries.id"), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


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


# --- Phase 26.6: End-to-End Client Financial Lifecycle Models ---

class Sponsor(Record, Base):
    __tablename__ = "billing_sponsors"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    reference_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    sponsor_type: Mapped[str] = mapped_column(String(50), default="FAMILY")  # FAMILY, EMPLOYER, NGO, CHURCH, INSURANCE, CORPORATE, OTHER
    contact_person: Mapped[str] = mapped_column(String(150), default="")
    email: Mapped[str] = mapped_column(String(150), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    billing_address: Mapped[str] = mapped_column(Text, default="")
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FinancialAssessment(Record, Base):
    __tablename__ = "billing_financial_assessments"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    reference_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    proposed_programme: Mapped[str] = mapped_column(String(150))
    expected_duration_days: Mapped[int] = mapped_column(Integer, default=90)
    expected_admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    primary_payer_type: Mapped[str] = mapped_column(String(50), default="SELF")  # SELF, FAMILY, EMPLOYER, CORPORATE, INSURANCE, NGO, CHURCH, GOVERNMENT, OTHER
    primary_payer_name: Mapped[str] = mapped_column(String(200))
    secondary_payer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_payer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sponsor_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_sponsors.id"), nullable=True, index=True)
    estimated_programme_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    deposit_required: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    credit_terms: Mapped[str] = mapped_column(String(100), default="30_DAYS")
    installment_preference: Mapped[str] = mapped_column(String(100), default="MONTHLY")
    discount_eligibility: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    authorization_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    financial_notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class FinancialQuotation(Record, Base):
    __tablename__ = "billing_quotations"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    assessment_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_financial_assessments.id"), nullable=True, index=True)
    reference_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)  # DRAFT, ISSUED, ACCEPTED, REJECTED, EXPIRED, CONVERTED
    programme_name: Mapped[str] = mapped_column(String(150))
    duration_days: Mapped[int] = mapped_column(Integer, default=90)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    deposit_required: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    valid_until: Mapped[date] = mapped_column(Date)
    terms_and_conditions: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    accepted_by: Mapped[str] = mapped_column(String(150), default="")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_agreement_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_financial_agreements.id", use_alter=True, name="fk_quotation_converted_agreement"), nullable=True)
    items: Mapped[list["FinancialQuotationItem"]] = relationship(back_populates="quotation", cascade="all, delete-orphan")


class FinancialQuotationItem(Record, Base):
    __tablename__ = "billing_quotation_items"
    quotation_id: Mapped[UUID] = mapped_column(ForeignKey("billing_quotations.id"), index=True)
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_services.id"), nullable=True)
    package_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_programme_packages.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="PROGRAMME")  # PROGRAMME, ACCOMMODATION, ASSESSMENT, LAB, MEDICATION, TRANSPORT, OTHER
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1.00"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quotation: Mapped["FinancialQuotation"] = relationship(back_populates="items")


class FinancialAgreement(Record, Base):
    __tablename__ = "billing_financial_agreements"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey("admissions.id"), nullable=True, index=True)
    quotation_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_quotations.id"), nullable=True, index=True)
    reference_code: Mapped[str] = mapped_column(String(50), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_agreement_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_financial_agreements.id"), nullable=True)
    revision_reason: Mapped[str] = mapped_column(Text, default="")
    programme_name: Mapped[str] = mapped_column(String(150))
    agreed_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    deposit_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    installment_terms: Mapped[str] = mapped_column(String(200), default="")
    credit_terms: Mapped[str] = mapped_column(String(100), default="")
    inclusions: Mapped[str] = mapped_column(Text, default="")
    exclusions: Mapped[str] = mapped_column(Text, default="")
    refund_terms: Mapped[str] = mapped_column(Text, default="")
    approved_discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    effective_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)  # DRAFT, PENDING_ACCEPTANCE, ACTIVE, REVISED, COMPLETED, CANCELLED
    accepted_by_name: Mapped[str] = mapped_column(String(150), default="")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class PackageServiceInclusion(Record, Base):
    __tablename__ = "billing_package_inclusions"
    package_id: Mapped[UUID] = mapped_column(ForeignKey("billing_programme_packages.id"), index=True)
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_services.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(50))  # COUNSELLING, PSYCHIATRY, NURSING, ACCOMMODATION, PHARMACY, LAB, OTHER
    classification: Mapped[str] = mapped_column(String(30), default="INCLUDED")  # INCLUDED, LIMITED_QUANTITY, DISCOUNTED, SEPARATELY_BILLABLE
    allowed_quantity: Mapped[int] = mapped_column(Integer, default=0)
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))


class PackageConsumption(Record, Base):
    __tablename__ = "billing_package_consumptions"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    package_id: Mapped[UUID] = mapped_column(ForeignKey("billing_programme_packages.id"), index=True)
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_services.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    quantity_allowed: Mapped[int] = mapped_column(Integer, default=0)
    quantity_used: Mapped[int] = mapped_column(Integer, default=0)
    quantity_remaining: Mapped[int] = mapped_column(Integer, default=0)


class RecurringBillingSchedule(Record, Base):
    __tablename__ = "billing_recurring_schedules"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    frequency: Mapped[str] = mapped_column(String(30))  # DAILY, WEEKLY, MONTHLY
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_services.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    next_run_date: Mapped[date] = mapped_column(Date, index=True)
    last_run_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_module: Mapped[str] = mapped_column(String(50), default="RECURRING")


class InvoicePayerAllocation(Record, Base):
    __tablename__ = "billing_invoice_payer_allocations"
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_payers.id"), nullable=True)
    sponsor_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_sponsors.id"), nullable=True)
    allocation_type: Mapped[str] = mapped_column(String(30), default="PERCENTAGE")  # PERCENTAGE, FIXED_AMOUNT
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    responsibility_description: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)  # PENDING, PARTIALLY_PAID, PAID


class PaymentPlan(Record, Base):
    __tablename__ = "billing_payment_plans"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey("admissions.id"), nullable=True, index=True)
    invoice_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_invoices.id"), nullable=True, index=True)
    reference_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    number_of_installments: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)  # DRAFT, ACTIVE, ON_TRACK, OVERDUE, DEFAULTED, COMPLETED, CANCELLED
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    installments: Mapped[list["PaymentPlanInstallment"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class PaymentPlanInstallment(Record, Base):
    __tablename__ = "billing_payment_plan_installments"
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("billing_payment_plans.id"), index=True)
    installment_number: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)  # PENDING, PARTIALLY_PAID, PAID, OVERDUE
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    plan: Mapped["PaymentPlan"] = relationship(back_populates="installments")


class ResidentFundAccount(Record, Base):
    __tablename__ = "billing_resident_fund_accounts"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey("admissions.id"), nullable=True, index=True)
    reference_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ResidentFundTransaction(Record, Base):
    __tablename__ = "billing_resident_fund_transactions"
    account_id: Mapped[UUID] = mapped_column(ForeignKey("billing_resident_fund_accounts.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(30))  # DEPOSIT, WITHDRAWAL, PURCHASE, RETURN_OF_FUNDS, ADJUSTMENT
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    running_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str] = mapped_column(Text, default="")
    receipt_reference: Mapped[str] = mapped_column(String(100), default="")
    payment_method: Mapped[str] = mapped_column(String(50), default="CASH")
    authorized_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    journal_id: Mapped[UUID | None] = mapped_column(ForeignKey("finance_journal_entries.id"), nullable=True)


class DischargeFinancialClearance(Record, Base):
    __tablename__ = "billing_discharge_clearances"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), unique=True, index=True)
    reference_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    total_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_payments: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_credits: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_refunds: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total_writeoffs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    outstanding_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)  # NOT_REVIEWED, PENDING, CLEARED, PAYMENT_PLAN, AUTHORIZED_EXCEPTION, REFUND_DUE
    has_payment_plan: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_payment_plans.id"), nullable=True)
    is_authorized_exception: Mapped[bool] = mapped_column(Boolean, default=False)
    exception_reason: Mapped[str] = mapped_column(Text, default="")
    exception_approved_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    collection_owner: Mapped[str] = mapped_column(String(150), default="")
    reviewed_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    clearance_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class BillingExportAudit(Record, Base):
    __tablename__ = "billing_export_audits"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    export_format: Mapped[str] = mapped_column(String(20))  # PDF, PRINT, CSV, XLSX, EMAIL
    report_type: Mapped[str] = mapped_column(String(80))
    reference_code: Mapped[str] = mapped_column(String(100), default="")
    filter_parameters: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
