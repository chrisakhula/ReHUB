"""Aftercare and recovery background tasks: milestone follow-up scheduling and overdue detection."""

from datetime import datetime, timezone
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models.discharge import AftercareCase, AftercareContact
from app.models.shared import Notification, Task
from app.tasks.base import run_idempotent_task

logger = logging.getLogger("rehub.tasks.aftercare")


def process_aftercare_milestones(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Scan active aftercare cases, calculate milestone due dates (7, 30, 90, 180, 365 days), and create staff follow-up tasks."""
    now = datetime.now(timezone.utc)
    query = select(AftercareCase).where(AftercareCase.status == "ACTIVE")
    if facility_id:
        query = query.where(AftercareCase.facility_id == facility_id)

    cases = list(db.scalars(query))
    tasks_created = 0
    overdue_notified = 0

    for case in cases:
        intervals = [int(i.strip()) for i in case.follow_up_intervals.split(",") if i.strip().isdigit()]
        contacts = list(
            db.scalars(
                select(AftercareContact).where(AftercareContact.case_id == case.id)
            )
        )
        days_since_start = (now - case.start_date.replace(tzinfo=timezone.utc)).days

        for interval in intervals:
            # If we're within 2 days of this milestone or past it
            if days_since_start >= (interval - 2):
                # Check if a contact was logged around this window (within interval +/- 7 days)
                contact_done = any(
                    abs((c.contact_date.replace(tzinfo=timezone.utc) - case.start_date.replace(tzinfo=timezone.utc)).days - interval) <= 7
                    for c in contacts
                )
                if not contact_done:
                    # Check if a task already exists for this milestone
                    existing_task = db.scalar(
                        select(Task).where(
                            Task.owner_id == case.assigned_staff_id,
                            Task.title == f"Aftercare Day-{interval} Follow-Up",
                        )
                    )
                    if not existing_task:
                        task = Task(
                            owner_id=case.assigned_staff_id,
                            title=f"Aftercare Day-{interval} Follow-Up",
                            description=f"Conduct recovery follow-up for aftercare case {case.id} (Milestone: Day {interval}).",
                            priority="high" if days_since_start > interval else "normal",
                            status="pending",
                        )
                        db.add(task)
                        tasks_created += 1

                    if days_since_start > (interval + 3):
                        # Overdue reminder notification
                        db.add(
                            Notification(
                                user_id=case.assigned_staff_id,
                                title=f"Overdue Aftercare Follow-Up (Day {interval})",
                                message=f"The Day {interval} recovery follow-up for client aftercare case is overdue.",
                                severity="warning",
                                link_url="/discharge",
                            )
                        )
                        overdue_notified += 1

    db.flush()
    logger.info("Aftercare milestone scan complete: %d tasks created, %d overdue alerts.", tasks_created, overdue_notified)
    return {"tasks_created": tasks_created, "overdue_alerts": overdue_notified}


@celery_app.task(name="app.tasks.aftercare.process_aftercare_milestones_task", bind=True)
def process_aftercare_milestones_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "process_aftercare_milestones",
        process_aftercare_milestones,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )
