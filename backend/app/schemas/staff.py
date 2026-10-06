"""Staff schemas."""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StaffProfileIn(RecordBase):
    user_id: UUID
    employee_number: str = Field(..., max_length=100)
    designation: str = Field(..., max_length=100)
    department: str = Field(..., max_length=100)
    qualifications: str = Field("", max_length=1000)
    professional_body: str = Field("", max_length=100)
    licence_number: str = Field("", max_length=100)
    licence_expiry: date | None = None
    employment_status: str = Field("ACTIVE", max_length=50)
    emergency_contact: str = Field("", max_length=200)


class StaffProfileOut(StaffProfileIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class StaffShiftIn(RecordBase):
    staff_id: UUID
    shift_date: date
    shift_type: str = Field(..., max_length=50)
    start_time: datetime
    end_time: datetime
    attended: bool = False
    notes: str = Field("", max_length=1000)


class StaffShiftOut(StaffShiftIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime
