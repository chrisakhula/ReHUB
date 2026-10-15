"""Compliance background tasks: Statutory licence expiry reminders and status updates."""

from datetime import date, timedelta
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models.compliance import ComplianceRegister
from app.models.identity import User
from app.models.shared import Notification
from app.tasks.base import run_idempotent_task

logger = logging.getLogger("rehub.tasks.compliance")


def check_compliance_expiry(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Scan statutory licences and compliance registers; notify on 90/60/30/14/7-day thresholds and flag EXPIRED."""
    today = date.today()
    query = select(ComplianceRegister).where(
        ComplianceRegister.expiry_date != None,
        ComplianceRegister.status.in_(["ACTIVE", "IN_RENEWAL"]),
    )
    if facility_id:
        query = query.where(ComplianceRegister.facility_id == facility_id)

    registers = list(db.scalars(query))
    expired_count = 0
    reminders_sent = 0

    # Find admin users for facility notifications
    admins = list(
        db.scalars(
            select(User)
            .join(User.roles)
            .where(User.active == True)
        )
    )

    alert_intervals = {90, 60, 30, 14, 7}

    for reg in registers:
        days_left = (reg.expiry_date - today).days

        if days_left < 0:
            reg.status = "EXPIRED"
            expired_count += 1
            # Notify admins of expiration
            for admin in admins:
                if any(r.name in {"System Administrator", "Compliance Officer"} for r in admin.roles):
                    db.add(
                        Notification(
                            user_id=admin.id,
                            title="Compliance Permit EXPIRED",
                            message=f"{reg.category} permit ({reg.authority} ref: {reg.reference_number}) expired on {reg.expiry_date}.",
                            severity="alert",
                            link_url="/compliance",
                        )
                    )
                    reminders_sent += 1
        elif days_left in alert_intervals or days_left <= 7:
            severity = "alert" if days_left <= 7 else "warning"
            # Send reminder notification
            target_users = set()
            if reg.responsible_person_id:
                target_users.add(reg.responsible_person_id)
            for admin in admins:
                if any(r.name in {"System Administrator", "Compliance Officer"} for r in admin.roles):
                    target_users.add(admin.id)

            for u_id in target_users:
                db.add(
                    Notification(
                        user_id=u_id,
                        title=f"Compliance Renewal Due ({days_left}d)",
                        message=f"{reg.category} permit ({reg.authority}) expires in {days_left} day(s) on {reg.expiry_date}.",
                        severity=severity,
                        link_url="/compliance",
                    )
                )
                reminders_sent += 1

    db.flush()
    logger.info("Compliance check complete: %d expired, %d reminders sent.", expired_count, reminders_sent)
    return {"expired_registers": expired_count, "reminders_sent": reminders_sent}


@celery_app.task(name="app.tasks.compliance.check_compliance_expiry_task", bind=True)
def check_compliance_expiry_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "check_compliance_expiry",
        check_compliance_expiry,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )
