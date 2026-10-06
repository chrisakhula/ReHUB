from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict

class DischargePlanBase(BaseModel):
    admission_id: uuid.UUID
    readiness_checked: bool = False
    summary: Optional[str] = None
    discharge_date: Optional[datetime] = None
    responsible_staff_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

class DischargePlanCreate(DischargePlanBase):
    pass

class DischargePlanResponse(DischargePlanBase):
    id: uuid.UUID

class AftercareCaseBase(BaseModel):
    client_id: uuid.UUID
    assigned_staff_id: uuid.UUID
    status: str = "active"
    start_date: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AftercareCaseCreate(AftercareCaseBase):
    pass

class AftercareCaseResponse(AftercareCaseBase):
    id: uuid.UUID
