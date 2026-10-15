"""Staff background tasks: Professional licensing expiry detection and compliance tracking."""

from datetime import date
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models.identity import User
from app.models.shared import Notification
from app.models.staff import StaffProfile
from app.tasks.base import run_idempotent_task

logger = logging.getLogger("rehub.tasks.staff")


def check_staff_licence_expiry(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Scan staff profiles for professional body licensing expiry (KMPDC, NCK, etc.)."""
    today = date.today()
    query = select(StaffProfile).where(
        StaffProfile.licence_expiry != None,
        StaffProfile.employment_status == "ACTIVE",
    )
    if facility_id:
        query = query.where(StaffProfile.facility_id == facility_id)

    profiles = list(db.scalars(query))
    expired_count = 0
    reminders_sent = 0

    admins = list(
        db.scalars(
            select(User)
            .join(User.roles)
            .where(User.active == True)
        )
    )

    alert_windows = {60, 30, 14, 7}

    for prof in profiles:
        days_left = (prof.licence_expiry - today).days

        if days_left <= 0:
            expired_count += 1
            # Notify staff member and HR admin
            db.add(
                Notification(
                    user_id=prof.user_id,
                    title="Professional Licence EXPIRED",
                    message=f"Your {prof.professional_body} licence ({prof.licence_number}) expired on {prof.licence_expiry}. Renewal required for clinical practice.",
                    severity="alert",
                    link_url="/staff",
                )
            )
            for admin in admins:
                if any(r.name in {"System Administrator", "Compliance Officer"} for r in admin.roles):
                    db.add(
                        Notification(
                            user_id=admin.id,
                            title="Staff Clinical Licence Expired",
                            message=f"Staff member {prof.employee_number} ({prof.designation}) has an expired {prof.professional_body} licence.",
                            severity="alert",
                            link_url="/staff",
                        )
                    )
                    reminders_sent += 1
        elif days_left in alert_windows or days_left <= 7:
            reminders_sent += 1
            severity = "alert" if days_left <= 7 else "warning"
            db.add(
                Notification(
                    user_id=prof.user_id,
                    title=f"Licence Renewal Due ({days_left}d)",
                    message=f"Your {prof.professional_body} licence ({prof.licence_number}) expires in {days_left} days on {prof.licence_expiry}.",
                    severity=severity,
                    link_url="/staff",
                )
            )

    db.flush()
    logger.info("Staff licence scan complete: %d expired, %d reminders sent.", expired_count, reminders_sent)
    return {"expired_licences": expired_count, "reminders_sent": reminders_sent}


@celery_app.task(name="app.tasks.staff.check_staff_licence_expiry_task", bind=True)
def check_staff_licence_expiry_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "check_staff_licence_expiry",
        check_staff_licence_expiry,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )
