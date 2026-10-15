"""Background task execution and observability models."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class BackgroundJobLog(Record, Base):
    __tablename__ = "background_job_logs"

    task_name: Mapped[str] = mapped_column(String(150), index=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)  # QUEUED, RUNNING, SUCCESS, FAILED, RETRYING, CANCELLED
    facility_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("facilities.id"), nullable=True, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_scheduled_execution: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
