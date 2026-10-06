"""Compliance schemas."""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ComplianceRegisterIn(RecordBase):
    category: str = Field(..., max_length=100)
    authority: str = Field(..., max_length=200)
    reference_number: str = Field("", max_length=100)
    issue_date: date | None = None
    expiry_date: date | None = None
    status: str = Field("ACTIVE", max_length=50)
    responsible_person_id: UUID | None = None
    attachments_url: str = Field("", max_length=1000)
    notes: str = Field("", max_length=2000)


class ComplianceRegisterOut(ComplianceRegisterIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class ComplianceInspectionIn(RecordBase):
    register_id: UUID | None = None
    title: str = Field(..., max_length=200)
    inspection_date: datetime
    inspector_name: str = Field(..., max_length=200)
    authority: str = Field(..., max_length=200)
    findings: str = Field("", max_length=2000)
    corrective_actions: str = Field("", max_length=2000)
    passed: bool = True
    status: str = Field("COMPLETED", max_length=50)


class ComplianceInspectionOut(ComplianceInspectionIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime
