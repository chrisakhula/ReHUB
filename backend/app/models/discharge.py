"""Discharge and recovery models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class DischargePlan(Record, Base):
    __tablename__ = "discharge_plans"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    
    # Mandatory readiness checks
    goals_achieved: Mapped[str] = mapped_column(Text, default="")
    unresolved_risks: Mapped[str] = mapped_column(Text, default="")
    relapse_prevention: Mapped[str] = mapped_column(Text, default="")
    accommodation: Mapped[str] = mapped_column(String(200), default="")
    family_support: Mapped[str] = mapped_column(String(200), default="")
    work_education: Mapped[str] = mapped_column(String(200), default="")
    support_groups: Mapped[str] = mapped_column(Text, default="")
    appointments: Mapped[str] = mapped_column(Text, default="")
    referrals: Mapped[str] = mapped_column(Text, default="")
    emergency_plans: Mapped[str] = mapped_column(Text, default="")
    
    # Logistics
    medication_instructions: Mapped[str] = mapped_column(Text, default="")
    belongings_returned: Mapped[bool] = mapped_column(Boolean, default=False)
    
    discharge_type: Mapped[str] = mapped_column(String(100), default="PLANNED") # PLANNED, AMA (Against Medical Advice), TRANSFER, DECEASED
    status: Mapped[str] = mapped_column(String(50), default="DRAFT") # DRAFT, PENDING_APPROVAL, APPROVED, DISCHARGED
    summary: Mapped[str] = mapped_column(Text, default="")
    
    discharge_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responsible_staff_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class AftercareCase(Record, Base):
    __tablename__ = "discharge_aftercare_cases"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey("admissions.id"), nullable=True)
    assigned_staff_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    follow_up_intervals: Mapped[str] = mapped_column(String(200), default="7,30,90,180,365") # Days
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE") # ACTIVE, COMPLETED, RELAPSED, LOST_TO_FOLLOW_UP
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AftercareContact(Record, Base):
    __tablename__ = "discharge_aftercare_contacts"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("discharge_aftercare_cases.id"), index=True)
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    contact_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    successful: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Recovery monitoring
    abstinence: Mapped[bool] = mapped_column(Boolean, default=True)
    support_participation: Mapped[str] = mapped_column(String(100), default="")
    employment_education: Mapped[str] = mapped_column(String(100), default="")
    housing: Mapped[str] = mapped_column(String(100), default="")
    family_relations: Mapped[str] = mapped_column(String(100), default="")
    medication_adherence: Mapped[str] = mapped_column(String(100), default="")
    wellbeing: Mapped[str] = mapped_column(String(100), default="")
    
    notes: Mapped[str] = mapped_column(Text, default="")
    referrals_made: Mapped[str] = mapped_column(Text, default="")


class RelapseRecord(Record, Base):
    __tablename__ = "discharge_relapse_records"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    case_id: Mapped[UUID | None] = mapped_column(ForeignKey("discharge_aftercare_cases.id"), nullable=True)
    reported_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    substance: Mapped[str] = mapped_column(String(200))
    date_of_relapse: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    triggers: Mapped[str] = mapped_column(Text, default="")
    circumstances: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(50)) # SLIP, FULL_RELAPSE
    consequences: Mapped[str] = mapped_column(Text, default="")
    protective_factors: Mapped[str] = mapped_column(Text, default="")
    intervention: Mapped[str] = mapped_column(Text, default="")
    clinical_review: Mapped[str] = mapped_column(Text, default="")
