"""Staff models."""

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


class StaffProfile(Record, Base):
    __tablename__ = "staff_profiles"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    
    employee_number: Mapped[str] = mapped_column(String(100), unique=True)
    designation: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100))
    
    qualifications: Mapped[str] = mapped_column(Text, default="")
    professional_body: Mapped[str] = mapped_column(String(100), default="")
    licence_number: Mapped[str] = mapped_column(String(100), default="")
    licence_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    employment_status: Mapped[str] = mapped_column(String(50), default="ACTIVE") # ACTIVE, ON_LEAVE, TERMINATED
    emergency_contact: Mapped[str] = mapped_column(String(200), default="")


class StaffShift(Record, Base):
    __tablename__ = "staff_shifts"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("staff_profiles.id"))
    
    shift_date: Mapped[date] = mapped_column(Date)
    shift_type: Mapped[str] = mapped_column(String(50)) # DAY, NIGHT, ON_CALL
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    attended: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
