"""Facility-scoped clinical records and append-only note/result history."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class CareRecord(Record):
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)


class ClinicalEncounter(CareRecord, Base):
    __tablename__ = "clinical_encounters"
    encounter_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    clinician_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    encounter_type: Mapped[str] = mapped_column(String(40), default="ROUTINE")
    presenting_complaint: Mapped[str] = mapped_column(Text)
    medical_history: Mapped[str] = mapped_column(Text, default="")
    physical_examination: Mapped[str] = mapped_column(Text, default="")
    diagnosis: Mapped[str] = mapped_column(Text, default="")
    assessment: Mapped[str] = mapped_column(Text, default="")
    plan: Mapped[str] = mapped_column(Text, default="")
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emergency_action: Mapped[str] = mapped_column(Text, default="")


class ClinicalRevision(Record, Base):
    __tablename__ = "clinical_note_revisions"
    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "version", name="uq_clinical_revision_version"
        ),
    )
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[UUID] = mapped_column(index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(500))


class ClinicalProblem(Record, Base):
    __tablename__ = "clinical_problems"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey("admissions.id"), index=True)
    diagnosis: Mapped[str] = mapped_column(String(500))
    code: Mapped[str | None] = mapped_column(String(50))
    onset_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str] = mapped_column(Text, default="")


class ClinicalAllergy(Record, Base):
    __tablename__ = "clinical_allergies"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    substance: Mapped[str] = mapped_column(String(200))
    reaction: Mapped[str] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")


class VitalSign(CareRecord, Base):
    __tablename__ = "clinical_vitals"
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    systolic: Mapped[int | None] = mapped_column(Integer)
    diastolic: Mapped[int | None] = mapped_column(Integer)
    pulse: Mapped[int | None] = mapped_column(Integer)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer)
    temperature: Mapped[float | None] = mapped_column(Float)
    oxygen_saturation: Mapped[float | None] = mapped_column(Float)
    weight: Mapped[float | None] = mapped_column(Float)
    height: Mapped[float | None] = mapped_column(Float)
    blood_glucose: Mapped[float | None] = mapped_column(Float)
    pain_score: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(String(1000), default="")


class MedicalOrder(CareRecord, Base):
    __tablename__ = "clinical_orders"
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("clinical_encounters.id"))
    order_type: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    destination: Mapped[str] = mapped_column(String(200), default="")
    priority: Mapped[str] = mapped_column(String(20), default="ROUTINE")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_note: Mapped[str] = mapped_column(Text, default="")


class NursingNote(CareRecord, Base):
    __tablename__ = "nursing_notes"
    noted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    shift: Mapped[str] = mapped_column(String(20))
    assessment: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    interventions: Mapped[str] = mapped_column(Text, default="")
    escalation: Mapped[str] = mapped_column(Text, default="")
    escalated_to_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    observation_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class NursingObservation(CareRecord, Base):
    __tablename__ = "nursing_observations"
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    appetite: Mapped[str] = mapped_column(String(30))
    mood: Mapped[str] = mapped_column(String(100))
    hygiene: Mapped[str] = mapped_column(String(30))
    withdrawal_symptoms: Mapped[str] = mapped_column(Text, default="")
    withdrawal_score: Mapped[int | None] = mapped_column(Integer)
    pain_score: Mapped[int | None] = mapped_column(Integer)
    interventions: Mapped[str] = mapped_column(Text, default="")
    escalation: Mapped[str] = mapped_column(Text, default="")
    next_observation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )


class ShiftHandover(Record, Base):
    __tablename__ = "nursing_handovers"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    shift_date: Mapped[date] = mapped_column(Date, index=True)
    shift: Mapped[str] = mapped_column(String(20))
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey("admissions.id"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    outstanding_tasks: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="ROUTINE")
    acknowledged_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LaboratoryRequest(CareRecord, Base):
    __tablename__ = "clinical_lab_requests"
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("clinical_encounters.id"))
    test: Mapped[str] = mapped_column(String(200))
    indication: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(200))
    specimen_type: Mapped[str] = mapped_column(String(100))
    specimen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[str] = mapped_column(String(20), default="ROUTINE")
    status: Mapped[str] = mapped_column(String(30), default="REQUESTED", index=True)


class LaboratoryResult(Record, Base):
    __tablename__ = "clinical_lab_results"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("clinical_lab_requests.id"), index=True)
    resulted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    result: Mapped[str] = mapped_column(Text)
    units: Mapped[str] = mapped_column(String(100), default="")
    reference_range: Mapped[str] = mapped_column(String(500), default="")
    abnormal_flag: Mapped[str] = mapped_column(String(30))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str] = mapped_column(Text, default="")
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class LaboratoryAttachment(Record, Base):
    __tablename__ = "clinical_lab_attachments"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("clinical_lab_requests.id"), index=True)
    filename: Mapped[str] = mapped_column(String(150))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)


class ToxicologyTest(CareRecord, Base):
    __tablename__ = "clinical_toxicology_tests"
    test_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reason: Mapped[str] = mapped_column(Text)
    sample_type: Mapped[str] = mapped_column(String(100))
    results: Mapped[list] = mapped_column(JSON)
    confirmatory_test: Mapped[str] = mapped_column(String(500), default="")
    confirmatory_result: Mapped[str] = mapped_column(String(500), default="")
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    acknowledgement: Mapped[str] = mapped_column(String(30))
    acknowledgement_note: Mapped[str] = mapped_column(String(1000), default="")
    follow_up_action: Mapped[str] = mapped_column(Text)

class CrisisAlert(Record, Base):
    __tablename__ = "clinical_crisis_alerts"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID | None] = mapped_column(ForeignKey("clients.id"), index=True)
    source_entity: Mapped[str] = mapped_column(String(50))
    source_entity_id: Mapped[str] = mapped_column(String(50))
    detected_keywords: Mapped[str] = mapped_column(String(500))
    text_snippet: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(30), default="CRITICAL")
    status: Mapped[str] = mapped_column(String(30), default="NEW")
    acknowledged_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

