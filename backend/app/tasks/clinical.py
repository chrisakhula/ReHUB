"""Clinical background tasks: Crisis alert escalation and overdue risk assessment review detection."""

from datetime import date, datetime, timedelta, timezone
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.models.clinical import CrisisAlert
from app.models.identity import User
from app.models.rehabilitation import RiskAssessment
from app.models.shared import Notification
from app.tasks.base import run_idempotent_task

logger = logging.getLogger("rehub.tasks.clinical")


def escalate_critical_alerts(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Escalate critical crisis alerts using institutional CrisisEscalationPolicy."""
    import asyncio
    from app.services.crisis import crisis_escalation_service

    escalated_count = asyncio.run(crisis_escalation_service.evaluate_escalations(db))
    logger.info("Escalated %d unacknowledged crisis alerts via policy engine.", escalated_count)
    return {"escalated_alerts": escalated_count}


def detect_overdue_risk_reviews(db: Session, facility_id: Optional[UUID] = None) -> dict:
    """Scan active clinical risk assessments and notify assigned staff if review_date has passed."""
    today = date.today()
    query = select(RiskAssessment).where(
        RiskAssessment.status == "ACTIVE",
        RiskAssessment.review_date <= today,
    )
    if facility_id:
        query = query.where(RiskAssessment.facility_id == facility_id)

    overdue_risks = list(db.scalars(query))
    notified_count = 0

    for risk in overdue_risks:
        notification = Notification(
            user_id=risk.assigned_staff_id,
            title="Clinical Risk Review Overdue",
            message=f"Risk assessment for {risk.risk_type} (Level: {risk.level}) was due for formal review on {risk.review_date}.",
            severity="warning",
            link_url="/rehabilitation",
        )
        db.add(notification)
        notified_count += 1

    db.flush()
    logger.info("Flagged %d overdue clinical risk reviews.", notified_count)
    return {"overdue_risk_reviews": notified_count}


@celery_app.task(name="app.tasks.clinical.escalate_critical_alerts_task", bind=True)
def escalate_critical_alerts_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "escalate_critical_alerts",
        escalate_critical_alerts,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )


@celery_app.task(name="app.tasks.clinical.detect_overdue_risk_reviews_task", bind=True)
def detect_overdue_risk_reviews_task(self, facility_id: Optional[str] = None):
    fac_uuid = UUID(facility_id) if facility_id else None
    return run_idempotent_task(
        "detect_overdue_risk_reviews",
        detect_overdue_risk_reviews,
        facility_id=fac_uuid,
        celery_task_id=self.request.id,
    )
