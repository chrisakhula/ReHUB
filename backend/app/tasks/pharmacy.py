"""Pharmacy background tasks: Expiring drug batches and low stock threshold alerts."""

from datetime import date, timedelta
from decimal import Decimal
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models.identity import User
from app.models.medication import DrugBatch, Medication
from app.models.shared import Notification
from app.tasks.base import run_idempotent_task

logger = logging.getLogger("rehub.tasks.pharmacy")


def check_pharmacy_batches(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Scan pharmacy batches for expiry dates and calculate total stock vs reorder levels."""
    today = date.today()
    query = select(DrugBatch).where(DrugBatch.quantity > 0)
    if facility_id:
        query = query.where(DrugBatch.facility_id == facility_id)

    batches = list(db.scalars(query))
    expired_count = 0
    expiring_soon_count = 0

    pharmacy_staff = list(
        db.scalars(
            select(User)
            .join(User.roles)
            .where(User.active == True)
        )
    )

    for batch in batches:
        days_left = (batch.expiry_date - today).days

        if days_left <= 0:
            expired_count += 1
            for user in pharmacy_staff:
                if any(r.name in {"Pharmacist", "Medical Officer"} for r in user.roles):
                    db.add(
                        Notification(
                            user_id=user.id,
                            title="EXPIRED Drug Batch in Stock",
                            message=f"Batch {batch.batch_number} expired on {batch.expiry_date} with {batch.quantity} {batch.unit} remaining. Quarantining required.",
                            severity="alert",
                            link_url="/pharmacy",
                        )
                    )
        elif days_left <= 60:
            expiring_soon_count += 1
            if days_left in {60, 30, 14, 7}:
                for user in pharmacy_staff:
                    if any(r.name == "Pharmacist" for r in user.roles):
                        db.add(
                            Notification(
                                user_id=user.id,
                                title=f"Drug Batch Expiring Soon ({days_left}d)",
                                message=f"Batch {batch.batch_number} will expire in {days_left} days on {batch.expiry_date}.",
                                severity="warning",
                                link_url="/pharmacy",
                            )
                        )

    # Check low stock vs reorder levels
    med_query = select(Medication).where(Medication.active == True, Medication.reorder_level > 0)
    if facility_id:
        med_query = med_query.where(Medication.facility_id == facility_id)

    medications = list(db.scalars(med_query))
    low_stock_count = 0

    for med in medications:
        total_qty = db.scalar(
            select(func.coalesce(func.sum(DrugBatch.quantity), Decimal("0"))).where(
                DrugBatch.medication_id == med.id,
                DrugBatch.expiry_date > today,
            )
        ) or Decimal("0")

        if total_qty <= med.reorder_level:
            low_stock_count += 1
            for user in pharmacy_staff:
                if any(r.name in {"Pharmacist", "Storekeeper"} for r in user.roles):
                    db.add(
                        Notification(
                            user_id=user.id,
                            title="Low Stock: Reorder Level Breached",
                            message=f"{med.generic_name} ({med.strength}) current stock {total_qty} {med.dose_unit} is at or below reorder level ({med.reorder_level}).",
                            severity="warning",
                            link_url="/pharmacy",
                        )
                    )

    db.flush()
    logger.info("Pharmacy scan complete: %d expired batches, %d expiring soon, %d low stock meds.", expired_count, expiring_soon_count, low_stock_count)
    return {
        "expired_batches": expired_count,
        "expiring_soon_batches": expiring_soon_count,
        "low_stock_medications": low_stock_count,
    }


@celery_app.task(name="app.tasks.pharmacy.check_pharmacy_batches_task", bind=True)
def check_pharmacy_batches_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "check_pharmacy_batches",
        check_pharmacy_batches,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )
