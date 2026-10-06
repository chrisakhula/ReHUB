from datetime import date, datetime
from typing import List, Optional
import uuid

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base

class StoreItem(Base):
    __tablename__ = "store_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    stock_level: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    reorder_level: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

class ComplianceRegister(Base):
    __tablename__ = "compliance_registers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    authority: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. NACADA, Pharmacy
    reference_number: Mapped[str] = mapped_column(String(100), nullable=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")

class StaffProfile(Base):
    __tablename__ = "staff_profiles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    employee_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    professional_body: Mapped[str] = mapped_column(String(100), nullable=True)
    licence_expiry: Mapped[date] = mapped_column(Date, nullable=True)
