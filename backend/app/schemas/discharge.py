"""Discharge and recovery schemas."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DischargePlanIn(RecordBase):
    admission_id: UUID
    goals_achieved: str = Field("", max_length=2000)
    unresolved_risks: str = Field("", max_length=2000)
    relapse_prevention: str = Field("", max_length=2000)
    accommodation: str = Field("", max_length=200)
    family_support: str = Field("", max_length=200)
    work_education: str = Field("", max_length=200)
    support_groups: str = Field("", max_length=1000)
    appointments: str = Field("", max_length=1000)
    referrals: str = Field("", max_length=1000)
    emergency_plans: str = Field("", max_length=1000)
    
    medication_instructions: str = Field("", max_length=2000)
    belongings_returned: bool = False
    
    discharge_type: str = Field("PLANNED", max_length=100)
    status: str = Field("DRAFT", max_length=50)
    summary: str = Field("", max_length=5000)
    discharge_date: datetime | None = None
    responsible_staff_id: UUID | None = None


class DischargePlanOut(DischargePlanIn):
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime


class AftercareCaseIn(RecordBase):
    client_id: UUID
    admission_id: UUID | None = None
    assigned_staff_id: UUID | None = None
    follow_up_intervals: str = Field("7,30,90,180,365", max_length=200)
    status: str = Field("ACTIVE", max_length=50)
    start_date: datetime


class AftercareCaseOut(AftercareCaseIn):
    id: UUID
    facility_id: UUID
    end_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AftercareContactIn(RecordBase):
    case_id: UUID
    contact_date: datetime
    successful: bool = True
    abstinence: bool = True
    support_participation: str = Field("", max_length=100)
    employment_education: str = Field("", max_length=100)
    housing: str = Field("", max_length=100)
    family_relations: str = Field("", max_length=100)
    medication_adherence: str = Field("", max_length=100)
    wellbeing: str = Field("", max_length=100)
    notes: str = Field("", max_length=2000)
    referrals_made: str = Field("", max_length=1000)


class AftercareContactOut(AftercareContactIn):
    id: UUID
    facility_id: UUID
    staff_id: UUID
    created_at: datetime
    updated_at: datetime


class RelapseRecordIn(RecordBase):
    client_id: UUID
    case_id: UUID | None = None
    substance: str = Field(..., max_length=200)
    date_of_relapse: datetime
    triggers: str = Field("", max_length=1000)
    circumstances: str = Field("", max_length=1000)
    severity: str = Field(..., max_length=50) # SLIP, FULL_RELAPSE
    consequences: str = Field("", max_length=1000)
    protective_factors: str = Field("", max_length=1000)
    intervention: str = Field("", max_length=1000)
    clinical_review: str = Field("", max_length=1000)


class RelapseRecordOut(RelapseRecordIn):
    id: UUID
    facility_id: UUID
    reported_by_id: UUID
    created_at: datetime
    updated_at: datetime
