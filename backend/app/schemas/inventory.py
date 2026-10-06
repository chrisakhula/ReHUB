"""Inventory and stores schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SupplierIn(RecordBase):
    name: str = Field(..., max_length=200)
    contact_person: str = Field("", max_length=100)
    phone: str = Field("", max_length=50)
    email: str = Field("", max_length=100)
    address: str = Field("", max_length=1000)
    is_active: bool = True


class SupplierOut(SupplierIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class StoreItemIn(RecordBase):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    category: str = Field(..., max_length=100)
    unit_of_measure: str = Field(..., max_length=50)
    reorder_level: float = Field(0, ge=0)
    is_active: bool = True


class StoreItemOut(StoreItemIn):
    id: UUID
    facility_id: UUID
    current_stock: float
    created_at: datetime
    updated_at: datetime


class PurchaseOrderIn(RecordBase):
    supplier_id: UUID
    order_number: str = Field(..., max_length=100)
    order_date: datetime
    status: str = Field("DRAFT", max_length=50)
    total_amount: float = Field(0, ge=0)


class PurchaseOrderOut(PurchaseOrderIn):
    id: UUID
    facility_id: UUID
    requested_by_id: UUID
    approved_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class StockTransactionIn(RecordBase):
    item_id: UUID
    transaction_type: str = Field(..., max_length=50)
    quantity: float
    batch_number: str = Field("", max_length=100)
    expiry_date: datetime | None = None
    reference: str = Field("", max_length=200)
    notes: str = Field("", max_length=1000)


class StockTransactionOut(StockTransactionIn):
    id: UUID
    facility_id: UUID
    performed_by_id: UUID
    created_at: datetime
    updated_at: datetime
