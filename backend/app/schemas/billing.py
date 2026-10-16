"""Schemas for billing, payments, and financial management."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

InvoiceStatus = Literal["DRAFT", "ISSUED", "PARTIAL", "PAID", "CANCELLED", "WRITTEN_OFF"]
PaymentStatus = Literal["PENDING", "COMPLETED", "FAILED", "REFUNDED"]


class RecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PayerIn(RecordBase):
    name: str = Field(..., max_length=255)
    payer_type: str = Field(..., max_length=50)
    contact_person: str = Field("", max_length=150)
    contact_email: str = Field("", max_length=150)
    contact_phone: str = Field("", max_length=50)
    billing_address: str = Field("", max_length=1000)
    is_active: bool = True


class PayerOut(PayerIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class BillingServiceIn(RecordBase):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    category: str = Field(..., max_length=100)
    description: str = Field("", max_length=1000)
    is_active: bool = True


class BillingServiceOut(BillingServiceIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class InvoiceItemIn(RecordBase):
    service_id: UUID | None = None
    package_id: UUID | None = None
    description: str = Field(..., max_length=255)
    quantity: Decimal = Field(Decimal("1.00"), ge=0)
    unit_price: Decimal = Field(..., ge=0)
    discount: Decimal = Field(Decimal("0.00"), ge=0)
    tax_rate: Decimal = Field(Decimal("0.00"), ge=0)


class InvoiceItemOut(InvoiceItemIn):
    id: UUID
    invoice_id: UUID
    total_price: Decimal
    created_at: datetime
    updated_at: datetime


class InvoiceIn(RecordBase):
    client_id: UUID
    admission_id: UUID | None = None
    payer_id: UUID | None = None
    invoice_number: str = Field(..., max_length=50)
    issue_date: date
    due_date: date
    status: InvoiceStatus = "DRAFT"
    notes: str = Field("", max_length=2000)
    items: list[InvoiceItemIn] = Field(default_factory=list)


class InvoiceOut(InvoiceIn):
    id: UUID
    facility_id: UUID
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemOut] = []


class PaymentIn(RecordBase):
    payer_id: UUID | None = None
    client_id: UUID | None = None
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., max_length=50)
    transaction_reference: str = Field(..., max_length=100)
    payment_date: datetime
    notes: str = Field("", max_length=1000)


class PaymentOut(PaymentIn):
    id: UUID
    facility_id: UUID
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime


class PaymentAllocationIn(RecordBase):
    invoice_id: UUID
    amount: Decimal = Field(..., gt=0)


class PaymentAllocationOut(PaymentAllocationIn):
    id: UUID
    payment_id: UUID
    allocated_at: datetime
    allocated_by: UUID
    created_at: datetime
    updated_at: datetime


class ReceiptOut(RecordBase):
    id: UUID
    payment_id: UUID
    receipt_number: str
    issued_at: datetime
    issued_by: UUID
    notes: str
    created_at: datetime
    updated_at: datetime


class StkPushIn(BaseModel):
    client_id: UUID
    invoice_id: UUID
    phone_number: str = Field(..., max_length=20)
    amount: Decimal = Field(..., gt=0)


class ManualAllocationIn(BaseModel):
    invoice_id: UUID
    notes: Optional[str] = ""


class MpesaTransactionOut(RecordBase):
    id: UUID
    facility_id: UUID
    transaction_reference: str
    phone_number: str
    amount: Decimal
    timestamp: datetime
    payer_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    merchant_request_id: Optional[str] = None
    checkout_request_id: Optional[str] = None
    response_code: Optional[str] = None
    customer_message: Optional[str] = None
    status: str
    reconciliation_status: str
    reconciled_payment_id: Optional[UUID] = None
    reconciled_by_id: Optional[UUID] = None
    reconciled_at: Optional[datetime] = None
    reconciliation_notes: Optional[str] = None


# --- Phase 26.5: Credit Notes ---

class CreditNoteIn(RecordBase):
    invoice_id: UUID
    amount: Decimal = Field(..., gt=0)
    reason_code: str = Field("OTHER", max_length=50)
    reason: str = Field(..., min_length=3, max_length=1000)


class CreditNoteApproveIn(RecordBase):
    approval_notes: str = Field("", max_length=1000)


class CreditNoteOut(RecordBase):
    id: UUID
    facility_id: UUID
    invoice_id: UUID
    credit_number: str
    amount: Decimal
    reason_code: str
    reason: str
    status: str
    issued_at: datetime
    issued_by: UUID
    requested_by: UUID | None = None
    requested_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    approval_notes: str = ""
    journal_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


# --- Phase 26.5: Write-Offs ---

class WriteOffIn(RecordBase):
    invoice_id: UUID
    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=3, max_length=1000)


class WriteOffApproveIn(RecordBase):
    approval_notes: str = Field("", max_length=1000)


class WriteOffOut(RecordBase):
    id: UUID
    facility_id: UUID
    invoice_id: UUID
    reference_code: str | None = None
    amount: Decimal
    reason: str
    status: str
    requested_by: UUID | None = None
    requested_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    written_off_at: datetime | None = None
    approval_notes: str = ""
    journal_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


# --- Phase 26.5: Integrity Checker ---

class IntegrityRecord(BaseModel):
    entity_type: str
    reference: str
    source_id: str
    billing_amount: Decimal
    gl_amount: Decimal
    difference: Decimal
    status: str  # MATCHED, MISMATCH, MISSING_JOURNAL, DUPLICATE_JOURNAL
    details: str = ""


class BillingGlIntegrityReport(BaseModel):
    facility_id: UUID
    scanned_at: datetime
    invoices_checked: int
    payments_checked: int
    writeoffs_checked: int
    credit_notes_checked: int
    total_records: int
    matched: int
    mismatches: int
    missing_journals: int
    duplicate_journals: int
    records: list[IntegrityRecord]


# --- Phase 26.6: End-to-End Client Financial Lifecycle Schemas ---

class SponsorIn(RecordBase):
    name: str = Field(..., max_length=200)
    sponsor_type: str = Field("FAMILY", max_length=50)
    contact_person: str = Field("", max_length=150)
    email: str = Field("", max_length=150)
    phone: str = Field("", max_length=50)
    billing_address: str = Field("", max_length=1000)
    credit_limit: Decimal = Field(Decimal("0.00"), ge=0)


class SponsorOut(SponsorIn):
    id: UUID
    facility_id: UUID
    reference_code: str
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FinancialAssessmentIn(RecordBase):
    client_id: UUID
    proposed_programme: str = Field(..., max_length=150)
    expected_duration_days: int = Field(90, gt=0)
    expected_admission_date: Optional[date] = None
    primary_payer_type: str = Field("SELF", max_length=50)
    primary_payer_name: str = Field(..., max_length=200)
    secondary_payer_type: Optional[str] = Field(None, max_length=50)
    secondary_payer_name: Optional[str] = Field(None, max_length=200)
    sponsor_id: Optional[UUID] = None
    estimated_programme_cost: Decimal = Field(Decimal("0.00"), ge=0)
    deposit_required: Decimal = Field(Decimal("0.00"), ge=0)
    credit_terms: str = Field("30_DAYS", max_length=100)
    installment_preference: str = Field("MONTHLY", max_length=100)
    discount_eligibility: Decimal = Field(Decimal("0.00"), ge=0, le=100)
    authorization_limit: Decimal = Field(Decimal("0.00"), ge=0)
    financial_notes: str = Field("", max_length=2000)


class FinancialAssessmentOut(FinancialAssessmentIn):
    id: UUID
    facility_id: UUID
    reference_code: str
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime


class FinancialQuotationItemIn(RecordBase):
    service_id: Optional[UUID] = None
    package_id: Optional[UUID] = None
    category: str = Field("PROGRAMME", max_length=50)
    description: str = Field(..., max_length=255)
    quantity: Decimal = Field(Decimal("1.00"), gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount: Decimal = Field(Decimal("0.00"), ge=0)
    tax_rate: Decimal = Field(Decimal("0.00"), ge=0)


class FinancialQuotationItemOut(FinancialQuotationItemIn):
    id: UUID
    quotation_id: UUID
    total_price: Decimal
    created_at: datetime
    updated_at: datetime


class FinancialQuotationIn(RecordBase):
    client_id: UUID
    assessment_id: Optional[UUID] = None
    programme_name: str = Field(..., max_length=150)
    duration_days: int = Field(90, gt=0)
    deposit_required: Decimal = Field(Decimal("0.00"), ge=0)
    valid_until: date
    terms_and_conditions: str = Field("", max_length=4000)
    notes: str = Field("", max_length=2000)
    items: list[FinancialQuotationItemIn] = Field(default_factory=list)


class FinancialQuotationOut(RecordBase):
    id: UUID
    facility_id: UUID
    client_id: UUID
    assessment_id: Optional[UUID] = None
    reference_code: str
    status: str
    programme_name: str
    duration_days: int
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    deposit_required: Decimal
    valid_until: date
    terms_and_conditions: str
    notes: str
    created_by: UUID
    accepted_by: str = ""
    accepted_at: Optional[datetime] = None
    converted_agreement_id: Optional[UUID] = None
    items: list[FinancialQuotationItemOut] = []
    created_at: datetime
    updated_at: datetime


class FinancialAgreementIn(RecordBase):
    client_id: UUID
    admission_id: Optional[UUID] = None
    quotation_id: Optional[UUID] = None
    programme_name: str = Field(..., max_length=150)
    agreed_price: Decimal = Field(..., ge=0)
    deposit_amount: Decimal = Field(Decimal("0.00"), ge=0)
    installment_terms: str = Field("", max_length=200)
    credit_terms: str = Field("", max_length=100)
    inclusions: str = Field("", max_length=4000)
    exclusions: str = Field("", max_length=4000)
    refund_terms: str = Field("", max_length=4000)
    approved_discount: Decimal = Field(Decimal("0.00"), ge=0)
    effective_date: date
    notes: str = Field("", max_length=2000)


class FinancialAgreementReviseIn(RecordBase):
    revision_reason: str = Field(..., min_length=3, max_length=2000)
    agreed_price: Decimal = Field(..., ge=0)
    deposit_amount: Decimal = Field(Decimal("0.00"), ge=0)
    installment_terms: str = Field("", max_length=200)
    inclusions: str = Field("", max_length=4000)
    exclusions: str = Field("", max_length=4000)


class FinancialAgreementApproveIn(RecordBase):
    notes: str = Field("", max_length=1000)


class FinancialAgreementOut(RecordBase):
    id: UUID
    facility_id: UUID
    client_id: UUID
    admission_id: Optional[UUID] = None
    quotation_id: Optional[UUID] = None
    reference_code: str
    version: int
    parent_agreement_id: Optional[UUID] = None
    revision_reason: str
    programme_name: str
    agreed_price: Decimal
    deposit_amount: Decimal
    deposit_paid: Decimal
    installment_terms: str
    credit_terms: str
    inclusions: str
    exclusions: str
    refund_terms: str
    approved_discount: Decimal
    effective_date: date
    status: str
    accepted_by_name: str
    accepted_at: Optional[datetime] = None
    authorized_by_id: Optional[UUID] = None
    authorized_at: Optional[datetime] = None
    notes: str
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime


class PackageServiceInclusionIn(RecordBase):
    service_id: Optional[UUID] = None
    category: str = Field(..., max_length=50)
    classification: str = Field("INCLUDED", max_length=30)
    allowed_quantity: int = Field(0, ge=0)
    discount_percentage: Decimal = Field(Decimal("0.00"), ge=0, le=100)


class PackageServiceInclusionOut(PackageServiceInclusionIn):
    id: UUID
    package_id: UUID
    created_at: datetime
    updated_at: datetime


class PackageConsumptionOut(RecordBase):
    id: UUID
    facility_id: UUID
    admission_id: UUID
    package_id: UUID
    service_id: Optional[UUID] = None
    category: str
    quantity_allowed: int
    quantity_used: int
    quantity_remaining: int
    created_at: datetime
    updated_at: datetime


class RecurringBillingScheduleIn(RecordBase):
    admission_id: UUID
    frequency: str = Field(..., max_length=30)  # DAILY, WEEKLY, MONTHLY
    service_id: Optional[UUID] = None
    description: str = Field(..., max_length=255)
    amount: Decimal = Field(..., gt=0)
    next_run_date: date


class RecurringBillingScheduleOut(RecurringBillingScheduleIn):
    id: UUID
    facility_id: UUID
    last_run_date: Optional[date] = None
    is_active: bool
    source_module: str
    created_at: datetime
    updated_at: datetime


class InvoicePayerAllocationIn(RecordBase):
    payer_id: Optional[UUID] = None
    sponsor_id: Optional[UUID] = None
    allocation_type: str = Field("PERCENTAGE", max_length=30)  # PERCENTAGE, FIXED_AMOUNT
    percentage: Decimal = Field(Decimal("0.00"), ge=0, le=100)
    allocated_amount: Decimal = Field(..., gt=0)
    responsibility_description: str = Field("", max_length=200)


class InvoicePayerAllocationOut(InvoicePayerAllocationIn):
    id: UUID
    invoice_id: UUID
    paid_amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class PaymentPlanInstallmentIn(RecordBase):
    installment_number: int = Field(..., gt=0)
    due_date: date
    amount: Decimal = Field(..., gt=0)


class PaymentPlanInstallmentOut(PaymentPlanInstallmentIn):
    id: UUID
    plan_id: UUID
    paid_amount: Decimal
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PaymentPlanIn(RecordBase):
    client_id: UUID
    admission_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    total_amount: Decimal = Field(..., gt=0)
    number_of_installments: int = Field(3, gt=0)
    notes: str = Field("", max_length=2000)
    installments: list[PaymentPlanInstallmentIn] = Field(default_factory=list)


class PaymentPlanOut(RecordBase):
    id: UUID
    facility_id: UUID
    client_id: UUID
    admission_id: Optional[UUID] = None
    invoice_id: Optional[UUID] = None
    reference_code: str
    total_amount: Decimal
    number_of_installments: int
    status: str
    notes: str
    created_by: UUID
    approved_by: Optional[UUID] = None
    installments: list[PaymentPlanInstallmentOut] = []
    created_at: datetime
    updated_at: datetime


class RefundRequestIn(RecordBase):
    client_id: UUID
    payment_id: Optional[UUID] = None
    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=3, max_length=1000)
    source_type: str = Field("CLIENT_DEPOSIT", max_length=50)  # CLIENT_DEPOSIT, REVENUE_ADJUSTMENT, OVERPAYMENT
    refund_method: str = Field("BANK", max_length=50)
    transaction_reference: str = Field("", max_length=100)


class RefundApproveIn(RecordBase):
    approval_notes: str = Field("", max_length=1000)


class RefundOut(RecordBase):
    id: UUID
    facility_id: UUID
    reference_code: Optional[str] = None
    client_id: Optional[UUID] = None
    payment_id: Optional[UUID] = None
    amount: Decimal
    reason: str
    source_type: str
    refund_method: str
    transaction_reference: str
    status: str
    requested_by: Optional[UUID] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: str = ""
    journal_id: Optional[UUID] = None
    processed_at: Optional[datetime] = None
    processed_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ResidentFundAccountOut(RecordBase):
    id: UUID
    facility_id: UUID
    client_id: UUID
    admission_id: Optional[UUID] = None
    reference_code: str
    current_balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResidentFundDepositIn(RecordBase):
    amount: Decimal = Field(..., gt=0)
    description: str = Field(..., min_length=3, max_length=500)
    payment_method: str = Field("CASH", max_length=50)
    receipt_reference: str = Field("", max_length=100)


class ResidentFundWithdrawIn(RecordBase):
    amount: Decimal = Field(..., gt=0)
    description: str = Field(..., min_length=3, max_length=500)
    transaction_type: str = Field("WITHDRAWAL", max_length=30)  # WITHDRAWAL, PURCHASE, RETURN_OF_FUNDS


class ResidentFundTransactionOut(RecordBase):
    id: UUID
    account_id: UUID
    transaction_type: str
    amount: Decimal
    running_balance: Decimal
    description: str
    receipt_reference: str
    payment_method: str
    authorized_by_id: UUID
    journal_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class DischargeClearanceReviewIn(RecordBase):
    status: str = Field("CLEARED", max_length=30)  # CLEARED, PAYMENT_PLAN, AUTHORIZED_EXCEPTION, REFUND_DUE
    payment_plan_id: Optional[UUID] = None
    is_authorized_exception: bool = False
    exception_reason: str = Field("", max_length=1000)
    collection_owner: str = Field("", max_length=150)
    notes: str = Field("", max_length=2000)


class DischargeClearanceApproveIn(RecordBase):
    notes: str = Field("", max_length=1000)


class DischargeFinancialClearanceOut(RecordBase):
    id: UUID
    facility_id: UUID
    client_id: UUID
    admission_id: UUID
    reference_code: str
    total_charges: Decimal
    total_payments: Decimal
    total_credits: Decimal
    total_refunds: Decimal
    total_writeoffs: Decimal
    outstanding_balance: Decimal
    status: str
    has_payment_plan: bool
    payment_plan_id: Optional[UUID] = None
    is_authorized_exception: bool
    exception_reason: str
    exception_approved_by_id: Optional[UUID] = None
    collection_owner: str
    reviewed_by_id: Optional[UUID] = None
    approved_by_id: Optional[UUID] = None
    clearance_date: Optional[datetime] = None
    notes: str
    created_at: datetime
    updated_at: datetime


class ClientFinancialAccountSummary(BaseModel):
    client_id: UUID
    client_name: str
    client_reference: str
    admission_id: Optional[UUID] = None
    admission_number: Optional[str] = None
    programme: Optional[str] = None
    total_charges: Decimal
    total_credits: Decimal
    total_payments: Decimal
    total_refunds: Decimal
    total_writeoffs: Decimal
    outstanding_balance: Decimal
    credit_balance: Decimal
    overdue_amount: Decimal
    active_payment_plan_id: Optional[UUID] = None
    active_payment_plan_status: Optional[str] = None
    financial_clearance_status: Optional[str] = None

    @property
    def net_outstanding_balance(self) -> Decimal:
        return self.outstanding_balance


class SponsorStatementClientRow(BaseModel):
    client_id: str
    client_name: str
    client_reference: str
    admission_number: str
    total_charges: Decimal
    total_paid: Decimal
    balance: Decimal


class SponsorStatementSummary(BaseModel):
    sponsor_id: UUID
    sponsor_name: str
    sponsor_reference: str
    sponsor_type: str
    credit_limit: Decimal
    total_charges: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal
    clients: list[SponsorStatementClientRow] = []


class BillingExportRequestIn(BaseModel):
    export_format: str = Field("PDF", max_length=20)  # PDF, CSV, XLSX, PRINT, EMAIL
    report_type: str = Field(..., max_length=80)
    filters: dict = Field(default_factory=dict)
    reason: str = Field("", max_length=500)
    recipient_email: Optional[str] = None


class BillingExportAuditOut(RecordBase):
    id: UUID
    facility_id: UUID
    user_id: UUID
    export_format: str
    report_type: str
    reference_code: str
    filter_parameters: str
    reason: str
    created_at: datetime
    updated_at: datetime
