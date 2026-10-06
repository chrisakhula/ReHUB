"""Residential operations and safeguarding models."""

from datetime import datetime, date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class ResidentMovement(Record, Base):
    __tablename__ = "residential_movements"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    movement_type: Mapped[str] = mapped_column(String(50)) # LEAVE, HOSPITAL, TRANSFER, AWOL, RETURN
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expected_return: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    destination: Mapped[str] = mapped_column(String(200), default="")
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Visitor(Record, Base):
    __tablename__ = "residential_visitors"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    relationship_to_client: Mapped[str] = mapped_column(String(100))
    id_number: Mapped[str] = mapped_column(String(100), default="")
    contact_phone: Mapped[str] = mapped_column(String(50), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class VisitorLog(Record, Base):
    __tablename__ = "residential_visitor_logs"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    visitor_id: Mapped[UUID] = mapped_column(ForeignKey("residential_visitors.id"), index=True)
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey("admissions.id"), index=True)
    check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_brought_in: Mapped[str] = mapped_column(Text, default="")
    visit_notes: Mapped[str] = mapped_column(Text, default="")
    incidents_during_visit: Mapped[bool] = mapped_column(Boolean, default=False)
    staff_authorizing_entry: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class Incident(Record, Base):
    __tablename__ = "residential_incidents"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    category: Mapped[str] = mapped_column(String(100)) # e.g. MEDICAL, BEHAVIORAL, SECURITY, FACILITY
    severity: Mapped[str] = mapped_column(String(50)) # LOW, MEDIUM, HIGH, CRITICAL
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(200), default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reported_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    assigned_to_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN") # OPEN, INVESTIGATING, CLOSED
    resolution_summary: Mapped[str] = mapped_column(Text, default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IncidentAddendum(Record, Base):
    __tablename__ = "residential_incident_addenda"
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("residential_incidents.id"), index=True)
    note: Mapped[str] = mapped_column(Text)
    added_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class SafeguardingRecord(Record, Base):
    __tablename__ = "residential_safeguarding_records"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    concern_type: Mapped[str] = mapped_column(String(100)) # e.g. ABUSE, NEGLECT, EXPLOITATION, SELF_HARM
    vulnerable_group: Mapped[str] = mapped_column(String(50)) # MINOR, ELDERLY, DISABLED
    description: Mapped[str] = mapped_column(Text)
    reported_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    escalation_level: Mapped[str] = mapped_column(String(50), default="INTERNAL") # INTERNAL, EXTERNAL_AUTHORITY
    escalated_to: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(50), default="OPEN")
    follow_up_action: Mapped[str] = mapped_column(Text, default="")


class Grievance(Record, Base):
    __tablename__ = "residential_grievances"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID | None] = mapped_column(ForeignKey("clients.id"), index=True)
    submitted_by: Mapped[str] = mapped_column(String(200)) # Name if anonymous/external or Client
    category: Mapped[str] = mapped_column(String(100)) # e.g. FOOD, STAFF, FACILITY, PEER
    description: Mapped[str] = mapped_column(Text)
    investigator_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="RECEIVED") # RECEIVED, INVESTIGATING, RESOLVED
    resolution: Mapped[str] = mapped_column(Text, default="")
    corrective_action: Mapped[str] = mapped_column(Text, default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MealPlan(Record, Base):
    __tablename__ = "residential_meal_plans"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    diet_type: Mapped[str] = mapped_column(String(100)) # STANDARD, DIABETIC, HALAL, VEGAN, HYPERTENSIVE
    allergies: Mapped[str] = mapped_column(Text, default="")
    special_requirements: Mapped[str] = mapped_column(Text, default="")
    prescribed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
