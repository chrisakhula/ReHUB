from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict
from enum import Enum

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIAL = "partial"
    PAID = "paid"
    CANCELLED = "cancelled"
    WRITTEN_OFF = "written_off"

class InvoiceBase(BaseModel):
    client_id: uuid.UUID
    payer_id: Optional[uuid.UUID] = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    total_amount: float
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceResponse(InvoiceBase):
    id: uuid.UUID
