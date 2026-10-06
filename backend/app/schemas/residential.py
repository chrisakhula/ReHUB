from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict
from enum import Enum

class MovementType(str, Enum):
    LEAVE = "leave"
    HOSPITAL = "hospital"
    TRANSFER = "transfer"
    AWOL = "awol"
    RETURN = "return"

class ResidentMovementBase(BaseModel):
    admission_id: uuid.UUID
    movement_type: MovementType
    timestamp: Optional[datetime] = None
    expected_return: Optional[datetime] = None
    reason: Optional[str] = None
    recorded_by_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

class ResidentMovementCreate(ResidentMovementBase):
    pass

class ResidentMovementResponse(ResidentMovementBase):
    id: uuid.UUID

class IncidentBase(BaseModel):
    category: str
    severity: str
    description: str
    reported_by_id: uuid.UUID
    status: str = "open"
    model_config = ConfigDict(from_attributes=True)

class IncidentCreate(IncidentBase):
    pass

class IncidentResponse(IncidentBase):
    id: uuid.UUID
    timestamp: Optional[datetime] = None
