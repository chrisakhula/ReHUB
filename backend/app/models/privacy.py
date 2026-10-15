"""ODPC Data Protection and Privacy Models (Kenya Data Protection Act 2019).

Provides data subject access requests (DSAR), breach registers, retention policies,
and controlled bulk export workflows with strict auditability.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.identity import Record, utcnow


class DataSubjectRequest(Record, Base):
    """DSAR and Data Subject Rights Management under KDPA 2019."""

    __tablename__ = "data_subject_requests"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True, nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clients.id"), index=True, nullable=True)
    request_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # ACCESS, CORRECTION, CONSENT_WITHDRAWAL, RESTRICTED_PROCESSING, DELETION_OBJECTION
    status: Mapped[str] = mapped_column(String(50), default="RECEIVED", index=True, nullable=False)  # RECEIVED, IDENTITY_VERIFIED, UNDER_REVIEW, FULFILLED, REJECTED, APPEALED
    channel: Mapped[str] = mapped_column(String(50), default="IN_PERSON", nullable=False)  # IN_PERSON, WRITTEN, EMAIL, PORTAL
    subject_name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_contact: Mapped[str | None] = mapped_column(String(150), nullable=True)
    request_details: Mapped[str] = mapped_column(Text, nullable=False)
    verification_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dpo_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class DataBreach(Record, Base):
    """Data Breach Incident Register with statutory ODPC 72-hour notification tracking."""

    __tablename__ = "data_breaches"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True, nullable=False)
    incident_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    incident_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    odpc_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    odpc_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    odpc_reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_subjects_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    affected_categories: Mapped[list | dict] = mapped_column(JSON, default=list, nullable=False)
    estimated_affected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    containment_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    remedial_measures: Mapped[str | None] = mapped_column(Text, nullable=True)
    dpo_signoff_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    dpo_signoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CONTAINED", index=True, nullable=False)  # CONTAINED, REPORTED_TO_ODPC, CLOSED


class RetentionPolicy(Record, Base):
    """Configurable record retention policies complying with Health and Data Protection laws."""

    __tablename__ = "retention_policies"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True, nullable=False)
    record_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)  # CLINICAL_ADMISSION, COUNSELLING_SESSION, PHARMACY_DISPENSING, FINANCIAL_LEDGER, STAFF_HR
    retention_period_years: Mapped[int] = mapped_column(Integer, nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", index=True, nullable=False)  # ACTIVE, REVIEW_DUE, LEGAL_HOLD, ARCHIVED, ELIGIBLE_FOR_DISPOSAL
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExportRequest(Record, Base):
    """Controlled, permissioned bulk data exports with strict authorization gating."""

    __tablename__ = "export_requests"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True, nullable=False)
    export_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # CLIENT_BULK, CLINICAL_BULK, FINANCE_BULK, REPORTS_BULK
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="CSV", nullable=False)  # CSV, JSON, XLSX
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING_APPROVAL", index=True, nullable=False)  # PENDING_APPROVAL, APPROVED, REJECTED, COMPLETED
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
