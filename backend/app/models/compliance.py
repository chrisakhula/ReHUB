"""Compliance models."""

from datetime import datetime, date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class ComplianceRegister(Record, Base):
    __tablename__ = "compliance_registers"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    
    category: Mapped[str] = mapped_column(String(100)) # NACADA, FACILITY, FIRE, PHARMACY, ODPC, PROFESSIONAL, INSURANCE
    authority: Mapped[str] = mapped_column(String(200))
    reference_number: Mapped[str] = mapped_column(String(100), default="")
    
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE") # ACTIVE, EXPIRED, IN_RENEWAL, SUSPENDED
    responsible_person_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    attachments_url: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class ComplianceInspection(Record, Base):
    __tablename__ = "compliance_inspections"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    register_id: Mapped[UUID | None] = mapped_column(ForeignKey("compliance_registers.id"), nullable=True)
    
    title: Mapped[str] = mapped_column(String(200))
    inspection_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    inspector_name: Mapped[str] = mapped_column(String(200))
    authority: Mapped[str] = mapped_column(String(200))
    
    findings: Mapped[str] = mapped_column(Text, default="")
    corrective_actions: Mapped[str] = mapped_column(Text, default="")
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED") # SCHEDULED, COMPLETED, FOLLOW_UP_REQUIRED
