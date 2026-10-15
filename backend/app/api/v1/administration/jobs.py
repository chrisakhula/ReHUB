"""Administrative background job monitoring and trigger endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.identity import User
from app.models.jobs import BackgroundJobLog
from app.tasks import (
    check_compliance_expiry_task,
    check_overdue_invoices_task,
    check_pharmacy_batches_task,
    check_staff_licence_expiry_task,
    detect_overdue_medications_task,
    detect_overdue_risk_reviews_task,
    escalate_critical_alerts_task,
    generate_emar_rounds_task,
    process_aftercare_milestones_task,
)

router = APIRouter(prefix="/administration/jobs", tags=["Administration Jobs"])

TASK_DISPATCHER = {
    "generate_emar_rounds": generate_emar_rounds_task,
    "detect_overdue_medications": detect_overdue_medications_task,
    "check_compliance_expiry": check_compliance_expiry_task,
    "process_aftercare_milestones": process_aftercare_milestones_task,
    "escalate_critical_alerts": escalate_critical_alerts_task,
    "detect_overdue_risk_reviews": detect_overdue_risk_reviews_task,
    "check_pharmacy_batches": check_pharmacy_batches_task,
    "check_staff_licence_expiry": check_staff_licence_expiry_task,
    "check_overdue_invoices": check_overdue_invoices_task,
}


class BackgroundJobLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_name: str
    celery_task_id: Optional[str] = None
    status: str
    facility_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    retries: int
    failure_message: Optional[str] = None
    next_scheduled_execution: Optional[datetime] = None
    created_at: datetime


class BackgroundJobListOut(BaseModel):
    items: list[BackgroundJobLogOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=BackgroundJobListOut)
def list_background_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    task_name: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("audit.view")),
):
    """List execution history of background tasks with status and duration filters."""
    query = select(BackgroundJobLog)
    if status:
        query = query.where(BackgroundJobLog.status == status.upper())
    if task_name:
        query = query.where(BackgroundJobLog.task_name == task_name)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.order_by(desc(BackgroundJobLog.created_at)).offset((page - 1) * page_size).limit(page_size)

    items = list(db.scalars(query))
    return BackgroundJobListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/trigger/{task_name}")
def trigger_background_job(
    task_name: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("settings.manage")),
):
    """Trigger an on-demand execution of an active background task."""
    if task_name not in TASK_DISPATCHER:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task name '{task_name}'. Available: {list(TASK_DISPATCHER.keys())}",
        )

    task_fn = TASK_DISPATCHER[task_name]
    try:
        # Run delay asynchronously if celery worker available, or synchronous fallback
        try:
            async_res = task_fn.delay(str(actor.facility_id) if actor.facility_id else None)
            task_id = async_res.id
        except Exception:
            # Fallback to direct synchronous execution
            result = task_fn(str(actor.facility_id) if actor.facility_id else None)
            task_id = "sync-exec"

        return {"message": f"Task '{task_name}' dispatched successfully", "task_id": task_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(exc)}")
