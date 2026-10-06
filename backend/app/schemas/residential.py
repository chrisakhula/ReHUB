"""Schemas for residential operations and safeguarding."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MovementType = Literal["LEAVE", "HOSPITAL", "TRANSFER", "AWOL", "RETURN"]
IncidentSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
IncidentStatus = Literal["OPEN", "INVESTIGATING", "CLOSED"]


class RecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ResidentMovementIn(RecordBase):
    admission_id: UUID
    movement_type: MovementType
    timestamp: datetime
    expected_return: datetime | None = None
    reason: str = Field("", max_length=1000)
    destination: str = Field("", max_length=200)
    approved_by: UUID | None = None


class ResidentMovementOut(ResidentMovementIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class VisitorIn(RecordBase):
    client_id: UUID
    name: str = Field(..., max_length=255)
    relationship_to_client: str = Field(..., max_length=100)
    id_number: str = Field("", max_length=100)
    contact_phone: str = Field("", max_length=50)
    approved: bool = False
    approved_by: UUID | None = None


class VisitorOut(VisitorIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class VisitorLogIn(RecordBase):
    visitor_id: UUID
    admission_id: UUID | None = None
    check_in: datetime
    check_out: datetime | None = None
    items_brought_in: str = Field("", max_length=1000)
    visit_notes: str = Field("", max_length=1000)
    incidents_during_visit: bool = False
    staff_authorizing_entry: UUID


class VisitorLogOut(VisitorLogIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class IncidentIn(RecordBase):
    category: str = Field(..., max_length=100)
    severity: IncidentSeverity
    description: str = Field(..., min_length=5)
    location: str = Field("", max_length=200)
    timestamp: datetime
    assigned_to_id: UUID | None = None
    status: IncidentStatus = "OPEN"
    resolution_summary: str = Field("", max_length=2000)


class IncidentOut(IncidentIn):
    id: UUID
    facility_id: UUID
    reported_by_id: UUID
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IncidentAddendumIn(RecordBase):
    incident_id: UUID
    note: str = Field(..., min_length=5)


class IncidentAddendumOut(IncidentAddendumIn):
    id: UUID
    added_by: UUID
    created_at: datetime
    updated_at: datetime


class SafeguardingRecordIn(RecordBase):
    client_id: UUID
    concern_type: str = Field(..., max_length=100)
    vulnerable_group: str = Field(..., max_length=50)
    description: str = Field(..., min_length=5)
    escalation_level: str = Field("INTERNAL", max_length=50)
    escalated_to: str = Field("", max_length=200)
    status: str = Field("OPEN", max_length=50)
    follow_up_action: str = Field("", max_length=1000)


class SafeguardingRecordOut(SafeguardingRecordIn):
    id: UUID
    facility_id: UUID
    reported_by_id: UUID
    created_at: datetime
    updated_at: datetime


class GrievanceIn(RecordBase):
    client_id: UUID | None = None
    submitted_by: str = Field(..., max_length=200)
    category: str = Field(..., max_length=100)
    description: str = Field(..., min_length=5)
    investigator_id: UUID | None = None
    status: str = Field("RECEIVED", max_length=50)
    resolution: str = Field("", max_length=2000)
    corrective_action: str = Field("", max_length=2000)


class GrievanceOut(GrievanceIn):
    id: UUID
    facility_id: UUID
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MealPlanIn(RecordBase):
    admission_id: UUID
    diet_type: str = Field(..., max_length=100)
    allergies: str = Field("", max_length=1000)
    special_requirements: str = Field("", max_length=1000)
    prescribed_by: UUID | None = None
    active: bool = True


class MealPlanOut(MealPlanIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime
