"""Pydantic schemas for ODPC Data Protection & Privacy workflows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Data Subject Request (DSAR) ---
class DataSubjectRequestCreate(BaseModel):
    client_id: Optional[uuid.UUID] = None
    request_type: str = Field(..., description="ACCESS, CORRECTION, CONSENT_WITHDRAWAL, RESTRICTED_PROCESSING, DELETION_OBJECTION")
    channel: str = Field(default="IN_PERSON", description="IN_PERSON, WRITTEN, EMAIL, PORTAL")
    subject_name: str
    subject_contact: Optional[str] = None
    request_details: str
    verification_method: Optional[str] = None


class DataSubjectRequestReview(BaseModel):
    status: str = Field(..., description="IDENTITY_VERIFIED, UNDER_REVIEW, FULFILLED, REJECTED, APPEALED")
    dpo_notes: Optional[str] = None
    action_taken: Optional[str] = None
    rejection_reason: Optional[str] = None


class DataSubjectRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_id: uuid.UUID
    client_id: Optional[uuid.UUID] = None
    request_number: str
    request_type: str
    status: str
    channel: str
    subject_name: str
    subject_contact: Optional[str] = None
    request_details: str
    verification_method: Optional[str] = None
    dpo_notes: Optional[str] = None
    action_taken: Optional[str] = None
    fulfilled_at: Optional[datetime] = None
    fulfilled_by: Optional[uuid.UUID] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# --- Data Breach Register ---
class DataBreachCreate(BaseModel):
    incident_date: datetime
    detected_date: datetime
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    affected_categories: List[str]
    estimated_affected_count: int = 0
    description: str
    containment_actions: Optional[str] = None


class DataBreachUpdate(BaseModel):
    root_cause: Optional[str] = None
    remedial_measures: Optional[str] = None
    containment_actions: Optional[str] = None
    odpc_notified: Optional[bool] = None
    odpc_reference_number: Optional[str] = None
    data_subjects_notified: Optional[bool] = None
    status: Optional[str] = None


class DataBreachSignoff(BaseModel):
    dpo_notes: str


class DataBreachOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_id: uuid.UUID
    incident_number: str
    incident_date: datetime
    detected_date: datetime
    severity: str
    odpc_notified: bool
    odpc_notified_at: Optional[datetime] = None
    odpc_reference_number: Optional[str] = None
    data_subjects_notified: bool
    affected_categories: Any
    estimated_affected_count: int
    description: str
    containment_actions: Optional[str] = None
    root_cause: Optional[str] = None
    remedial_measures: Optional[str] = None
    dpo_signoff_by: Optional[uuid.UUID] = None
    dpo_signoff_at: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: datetime


# --- Retention Policy ---
class RetentionPolicyCreate(BaseModel):
    record_type: str
    retention_period_years: int
    legal_basis: str
    description: str = ""


class RetentionPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_id: uuid.UUID
    record_type: str
    retention_period_years: int
    legal_basis: str
    description: str
    status: str
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# --- Controlled Export Requests ---
class ExportRequestCreate(BaseModel):
    export_type: str = Field(..., description="CLIENT_BULK, CLINICAL_BULK, FINANCE_BULK, REPORTS_BULK")
    filters: Optional[dict] = None
    reason: str = Field(..., min_length=10, description="Mandatory institutional justification for bulk export")
    format: str = Field(default="CSV", description="CSV, JSON, XLSX")


class ExportRequestApprove(BaseModel):
    decision: str = Field(..., description="APPROVE, REJECT")
    notes: Optional[str] = None


class ExportRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_id: uuid.UUID
    export_type: str
    filters: Optional[dict] = None
    record_count: int
    reason: str
    format: str
    requested_by: uuid.UUID
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    status: str
    downloaded_at: Optional[datetime] = None
    download_count: int
    created_at: datetime
