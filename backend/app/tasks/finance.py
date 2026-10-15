"""Finance background tasks: Overdue invoice detection, debt ageing alerts, and reconciliation reminders."""

from datetime import date, datetime, timedelta, timezone
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models.billing import Invoice, MpesaTransaction
from app.models.identity import User
from app.models.shared import Notification
from app.tasks.base import run_idempotent_task

logger = logging.getLogger("rehub.tasks.finance")


def check_overdue_invoices(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Scan unpaid invoices with past due_dates and flag overdue debt ageing; alert on unmatched payments."""
    today = date.today()
    query = select(Invoice).where(
        Invoice.status.in_(["ISSUED", "PARTIAL"]),
        Invoice.due_date < today,
    )
    if facility_id:
        query = query.where(Invoice.facility_id == facility_id)

    overdue_invoices = list(db.scalars(query))
    overdue_count = len(overdue_invoices)

    # Check unallocated M-Pesa transactions older than 24 hours
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    unreconciled_mpesa = list(
        db.scalars(
            select(MpesaTransaction).where(
                MpesaTransaction.status.in_(["PENDING", "MANUAL_REVIEW"]),
                MpesaTransaction.created_at <= cutoff_24h,
            )
        )
    )
    unreconciled_count = len(unreconciled_mpesa)

    # Notify finance staff
    finance_staff = list(
        db.scalars(
            select(User)
            .join(User.roles)
            .where(User.active == True)
        )
    )

    for user in finance_staff:
        if any(r.name in {"Finance Officer", "System Administrator"} for r in user.roles):
            if overdue_count > 0:
                db.add(
                    Notification(
                        user_id=user.id,
                        title=f"{overdue_count} Invoices Currently Overdue",
                        message=f"There are {overdue_count} client invoices past due date awaiting payment follow-up or debt review.",
                        severity="warning",
                        link_url="/billing",
                    )
                )
            if unreconciled_count > 0:
                db.add(
                    Notification(
                        user_id=user.id,
                        title=f"{unreconciled_count} Unmatched Payments (> 24h)",
                        message=f"There are {unreconciled_count} M-Pesa transactions older than 24h requiring manual allocation.",
                        severity="warning",
                        link_url="/finance",
                    )
                )

    db.flush()
    logger.info("Finance scan complete: %d overdue invoices, %d unreconciled transactions.", overdue_count, unreconciled_count)
    return {"overdue_invoices": overdue_count, "unreconciled_mpesa": unreconciled_count}


@celery_app.task(name="app.tasks.finance.check_overdue_invoices_task", bind=True)
def check_overdue_invoices_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "check_overdue_invoices",
        check_overdue_invoices,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )
