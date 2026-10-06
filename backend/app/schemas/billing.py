"""Schemas for billing, payments, and financial management."""

from datetime import date, datetime
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
    quantity: float = Field(1, ge=0)
    unit_price: float = Field(..., ge=0)
    discount: float = Field(0, ge=0)
    tax_rate: float = Field(0, ge=0)


class InvoiceItemOut(InvoiceItemIn):
    id: UUID
    invoice_id: UUID
    total_price: float
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
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemOut] = []


class PaymentIn(RecordBase):
    payer_id: UUID | None = None
    client_id: UUID | None = None
    amount: float = Field(..., gt=0)
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
    amount: float = Field(..., gt=0)


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
