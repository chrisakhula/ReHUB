"""Schemas for the finance ledger module."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

AccountType = Literal["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE", "COGS"]
NormalBalance = Literal["DEBIT", "CREDIT"]
PeriodStatus = Literal["OPEN", "LOCKED", "CLOSED"]
JournalStatus = Literal["DRAFT", "SUBMITTED", "POSTED", "REVERSED"]


class RecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageOut(BaseModel):
    items: list[dict]
    meta: dict


class AccountIn(RecordBase):
    code: str = Field(..., max_length=30)
    name: str = Field(..., max_length=200)
    type: AccountType
    normal_balance: NormalBalance | None = None
    description: str = Field("", max_length=2000)
    is_active: bool = True


class FiscalPeriodIn(RecordBase):
    name: str = Field(..., max_length=120)
    start_date: date
    end_date: date
    notes: str = Field("", max_length=2000)

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class JournalLineIn(RecordBase):
    account_id: UUID | None = None
    account_code: str | None = None
    debit: Decimal = Field(0, ge=0)
    credit: Decimal = Field(0, ge=0)
    description: str = Field("", max_length=1000)


class ManualJournalIn(RecordBase):
    entry_date: date
    reference: str = Field("", max_length=120)
    description: str = Field(..., max_length=2000)
    lines: list[JournalLineIn] = Field(..., min_length=2)


class ExpenseCategoryIn(RecordBase):
    name: str = Field(..., max_length=150)
    description: str = Field("", max_length=2000)
    account_id: UUID
    is_active: bool = True


class ExpenseVoucherIn(RecordBase):
    expense_category_id: UUID
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., max_length=50)
    payment_account_id: UUID | None = None
    paid_to: str = Field(..., max_length=200)
    reference: str = Field("", max_length=120)
    description: str = Field("", max_length=2000)
    expense_date: date


class SupplierIn(RecordBase):
    name: str = Field(..., max_length=200)
    contact_person: str = Field("", max_length=150)
    email: str = Field("", max_length=150)
    phone: str = Field("", max_length=50)
    tax_pin: str = Field("", max_length=50)
    address: str = Field("", max_length=2000)
    is_active: bool = True


class SupplierInvoiceItemIn(RecordBase):
    account_id: UUID
    description: str = Field(..., max_length=255)
    quantity: Decimal = Field(1, gt=0)
    unit_cost: Decimal = Field(..., ge=0)
    discount: Decimal = Field(0, ge=0)
    tax_rate: Decimal = Field(0, ge=0)


class SupplierInvoiceIn(RecordBase):
    supplier_id: UUID
    invoice_number: str = Field(..., max_length=100)
    invoice_date: date
    due_date: date
    invoice_type: str = Field("DIRECT_EXPENSE", max_length=30)
    notes: str = Field("", max_length=2000)
    items: list[SupplierInvoiceItemIn] = Field(..., min_length=1)


class SupplierPaymentIn(RecordBase):
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., max_length=50)
    payment_account_id: UUID
    payment_reference: str = Field("", max_length=120)
    payment_date: date


class CashReconciliationIn(RecordBase):
    period_date: date
    cashier_name: str = Field("", max_length=150)
    opening_cash: Decimal = Field(0, ge=0)
    expected_cash: Decimal = Field(..., ge=0)
    counted_cash: Decimal = Field(..., ge=0)
    notes: str = Field("", max_length=2000)


class PaymentReconciliationIn(RecordBase):
    method: str = Field(..., max_length=50)
    period_date: date
    system_total: Decimal = Field(..., ge=0)
    statement_total: Decimal = Field(..., ge=0)
    missing_references: str = Field("", max_length=5000)
    duplicate_references: str = Field("", max_length=5000)


class JournalOut(RecordBase):
    id: UUID
    entry_date: date
    reference: str
    description: str
    source_module: str
    posting_type: str
    status: JournalStatus | str
    created_at: datetime
