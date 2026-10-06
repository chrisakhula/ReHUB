"""Admission-linked rehabilitation records, with append-only clinical revisions."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class FacilityRecord(Record):
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True)


class AdmissionRecord(FacilityRecord):
    admission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admissions.id"), index=True)


class Substance(FacilityRecord, Base):
    __tablename__ = "rehab_substances"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)
    name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SubstanceHistory(AdmissionRecord, Base):
    __tablename__ = "substance_histories"
    __table_args__ = (CheckConstraint("first_use_age >= 0 AND first_use_age <= 120"),)
    substance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rehab_substances.id"), index=True)
    first_use_age: Mapped[int | None] = mapped_column(Integer)
    regular_use_age: Mapped[int | None] = mapped_column(Integer)
    frequency: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[str] = mapped_column(String(150))
    route: Mapped[str] = mapped_column(String(100))
    duration: Mapped[str] = mapped_column(String(150), default="")
    last_use: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    typical_pattern: Mapped[str] = mapped_column(Text, default="")
    maximum_use: Mapped[str] = mapped_column(Text, default="")
    withdrawal_symptoms: Mapped[str] = mapped_column(Text, default="")
    tolerance: Mapped[str] = mapped_column(Text, default="")
    overdose: Mapped[str] = mapped_column(Text, default="")
    previous_quit_attempts: Mapped[str] = mapped_column(Text, default="")
    longest_abstinence: Mapped[str] = mapped_column(String(150), default="")
    previous_treatment: Mapped[str] = mapped_column(Text, default="")
    consequences: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="CURRENT")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("substance_histories.id"), unique=True
    )
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class AssessmentInstrument(FacilityRecord, Base):
    __tablename__ = "assessment_instruments"
    __table_args__ = (
        UniqueConstraint("facility_id", "code", "version"),
        CheckConstraint("version > 0"),
    )
    code: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(150))
    version: Mapped[int] = mapped_column(Integer, default=1)
    instructions: Mapped[str] = mapped_column(Text, default="")
    questions: Mapped[list] = mapped_column(JSON)
    score_bands: Mapped[list] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class InstrumentAssessment(AdmissionRecord, Base):
    __tablename__ = "instrument_assessments"
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_instruments.id"), index=True
    )
    responses: Mapped[dict] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    domain_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    interpretation: Mapped[str] = mapped_column(String(500))
    risk_level: Mapped[str] = mapped_column(String(20))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str] = mapped_column(Text, default="")


class BiopsychosocialAssessment(AdmissionRecord, Base):
    __tablename__ = "biopsychosocial_assessments"
    __table_args__ = (CheckConstraint("status IN ('DRAFT','COMPLETED','REVIEWED')"),)
    biological: Mapped[dict] = mapped_column(JSON)
    psychological: Mapped[dict] = mapped_column(JSON)
    social: Mapped[dict] = mapped_column(JSON)
    substance_use: Mapped[dict] = mapped_column(JSON)
    legal: Mapped[dict] = mapped_column(JSON)
    occupational: Mapped[dict] = mapped_column(JSON)
    spiritual: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("biopsychosocial_assessments.id"), unique=True
    )
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class RiskAssessment(AdmissionRecord, Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("level IN ('LOW','MODERATE','HIGH','CRITICAL')"),
        CheckConstraint("status IN ('ACTIVE','RESOLVED')"),
    )
    risk_type: Mapped[str] = mapped_column(String(50), index=True)
    level: Mapped[str] = mapped_column(String(20), index=True)
    risk_factors: Mapped[str] = mapped_column(Text)
    protective_factors: Mapped[str] = mapped_column(Text, default="")
    intervention: Mapped[str] = mapped_column(Text)
    assigned_staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    review_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_assessments.id"), unique=True
    )
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class TreatmentPlan(AdmissionRecord, Base):
    __tablename__ = "treatment_plans"
    __table_args__ = (
        CheckConstraint("version > 0"),
        CheckConstraint(
            "status IN ('DRAFT','ACTIVE','UNDER_REVIEW','REVISED','COMPLETED','CANCELLED')"
        ),
    )
    root_id: Mapped[uuid.UUID] = mapped_column(index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    presenting_problem: Mapped[str] = mapped_column(Text)
    problem_area: Mapped[str] = mapped_column(String(300))
    goal: Mapped[str] = mapped_column(Text)
    objectives: Mapped[list] = mapped_column(JSON)
    responsible_professional_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    start_date: Mapped[date] = mapped_column(Date)
    target_date: Mapped[date] = mapped_column(Date)
    review_date: Mapped[date] = mapped_column(Date, index=True)
    outcome: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("treatment_plans.id"), unique=True
    )
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class CaseAssignment(AdmissionRecord, Base):
    __tablename__ = "case_assignments"
    case_manager_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    counsellor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    team_member_ids: Mapped[list] = mapped_column(JSON, default=list)
    assessment_due: Mapped[date | None] = mapped_column(Date)
    family_meeting_due: Mapped[date | None] = mapped_column(Date)
    discharge_preparation_due: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("case_assignments.id"), unique=True
    )
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class TherapySession(AdmissionRecord, Base):
    __tablename__ = "therapy_sessions"
    __table_args__ = (
        CheckConstraint("end_at > start_at"),
        CheckConstraint("status IN ('SCHEDULED','COMPLETED','MISSED','CANCELLED')"),
    )
    session_type: Mapped[str] = mapped_column(String(70))
    therapist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    objective: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    intervention: Mapped[str] = mapped_column(Text, default="")
    client_response: Mapped[str] = mapped_column(Text, default="")
    progress: Mapped[str] = mapped_column(Text, default="")
    homework: Mapped[str] = mapped_column(Text, default="")
    risk_concerns: Mapped[str] = mapped_column(Text, default="")
    next_session: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidential: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("therapy_sessions.id"), unique=True
    )
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class GroupSession(FacilityRecord, Base):
    __tablename__ = "group_sessions"
    title: Mapped[str] = mapped_column(String(200))
    session_type: Mapped[str] = mapped_column(String(70))
    topic: Mapped[str] = mapped_column(String(300))
    facilitator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    co_facilitator_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(200))
    objectives: Mapped[str] = mapped_column(Text)


class GroupAttendance(AdmissionRecord, Base):
    __tablename__ = "group_attendances"
    __table_args__ = (CheckConstraint("status IN ('PRESENT','ABSENT','EXCUSED','REFUSED','LATE')"),)
    group_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("group_sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    private_observation: Mapped[str] = mapped_column(Text, default="")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("group_attendances.id"), unique=True
    )
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class ProgrammeActivity(FacilityRecord, Base):
    __tablename__ = "programme_activities"
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    programme: Mapped[str] = mapped_column(String(150), default="")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    recurrence: Mapped[str] = mapped_column(String(10), default="ONCE")
    repeat_until: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str] = mapped_column(String(200))
    facilitator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ProgrammeAttendance(AdmissionRecord, Base):
    __tablename__ = "programme_attendances"
    __table_args__ = (CheckConstraint("status IN ('PRESENT','ABSENT','EXCUSED','REFUSED','LATE')"),)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programme_activities.id"), index=True
    )
    occurrence_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(Text, default="")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("programme_attendances.id"), unique=True
    )
    correction_reason: Mapped[str] = mapped_column(String(500), default="")


class FamilyCommunication(AdmissionRecord, Base):
    __tablename__ = "family_communications"
    consent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consents.id"), index=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_contacts.id"))
    communicated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    method: Mapped[str] = mapped_column(String(30))
    purpose: Mapped[str] = mapped_column(Text)
    shared_information: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text, default="")
    next_meeting_date: Mapped[date | None] = mapped_column(Date)
