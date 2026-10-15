"""Medication background tasks: eMAR round generation and overdue dose detection."""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models.clients import Admission
from app.models.identity import Facility, User
from app.models.medication import MedicationAdministration, Prescription
from app.models.shared import Notification
from app.tasks.base import run_idempotent_task

logger = logging.getLogger("rehub.tasks.medication")


def generate_emar_rounds(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Generate scheduled medication administration rounds for active prescriptions."""
    now = datetime.now(timezone.utc)
    query = (
        select(Prescription)
        .join(Admission, Prescription.admission_id == Admission.id)
        .where(
            Prescription.status == "ACTIVE",
            Admission.status == "ACTIVE",
            Prescription.start_date <= now,
            (Prescription.end_date == None) | (Prescription.end_date >= now),
        )
    )
    if facility_id:
        query = query.where(Admission.facility_id == facility_id)

    active_prescriptions = list(db.scalars(query))
    created_count = 0

    # Common standard round hours: 06:00, 12:00, 18:00, 22:00
    today = now.date()
    round_times = [
        datetime(today.year, today.month, today.day, 6, 0, tzinfo=timezone.utc),
        datetime(today.year, today.month, today.day, 12, 0, tzinfo=timezone.utc),
        datetime(today.year, today.month, today.day, 18, 0, tzinfo=timezone.utc),
        datetime(today.year, today.month, today.day, 22, 0, tzinfo=timezone.utc),
    ]

    for rx in active_prescriptions:
        for r_time in round_times:
            # Check if an administration is already created for this prescription at this scheduled time
            existing = db.scalar(
                select(MedicationAdministration).where(
                    MedicationAdministration.prescription_id == rx.id,
                    MedicationAdministration.scheduled_time == r_time,
                )
            )
            if not existing:
                admin_record = MedicationAdministration(
                    prescription_id=rx.id,
                    scheduled_time=r_time,
                    status="SCHEDULED",
                    dose=rx.dose,
                    route=rx.route,
                )
                db.add(admin_record)
                created_count += 1

    db.flush()
    logger.info("Generated %d eMAR administration records.", created_count)
    return {"generated_administrations": created_count}


def detect_overdue_medications(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Flag scheduled medication doses that have passed scheduled time by > 60 minutes without administration."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=60)

    query = (
        select(MedicationAdministration)
        .where(
            MedicationAdministration.status == "SCHEDULED",
            MedicationAdministration.scheduled_time <= cutoff,
        )
    )
    overdue_list = list(db.scalars(query))
    flagged_count = 0

    if overdue_list:
        # Notify nursing staff
        nurses = list(
            db.scalars(
                select(User)
                .join(User.roles)
                .where(User.active == True)
            )
        )
        for admin_record in overdue_list:
            admin_record.status = "OVERDUE"
            flagged_count += 1
            for nurse in nurses:
                if any(r.name in {"Nurse", "Medical Officer"} for r in nurse.roles):
                    notification = Notification(
                        user_id=nurse.id,
                        title="Overdue Medication Alert",
                        message=f"Medication scheduled for {admin_record.scheduled_time.strftime('%H:%M')} is overdue for administration.",
                        severity="alert",
                        link_url="/nursing",
                    )
                    db.add(notification)

    db.flush()
    logger.info("Detected and flagged %d overdue medication administrations.", flagged_count)
    return {"overdue_administrations": flagged_count}


@celery_app.task(name="app.tasks.medication.generate_emar_rounds_task", bind=True)
def generate_emar_rounds_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "generate_emar_rounds",
        generate_emar_rounds,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )


@celery_app.task(name="app.tasks.medication.detect_overdue_medications_task", bind=True)
def detect_overdue_medications_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "detect_overdue_medications",
        detect_overdue_medications,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )
