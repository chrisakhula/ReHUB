"""Base task execution and observability harness for background jobs."""

from datetime import datetime, timezone
import logging
import traceback
from typing import Callable, Optional
from uuid import UUID

from app.core.database import SessionLocal
from app.models.jobs import BackgroundJobLog

logger = logging.getLogger("rehub.tasks")


def run_idempotent_task(
    task_name: str,
    task_fn: Callable,
    facility_id: Optional[UUID] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[UUID] = None,
    celery_task_id: Optional[str] = None,
    next_scheduled_execution: Optional[datetime] = None,
):
    """Execute a task function within an auditable, logged, and isolated database transaction."""
    started_at = datetime.now(timezone.utc)
    job_log = None

    with SessionLocal() as db:
        try:
            job_log = BackgroundJobLog(
                task_name=task_name,
                celery_task_id=celery_task_id,
                status="RUNNING",
                facility_id=facility_id,
                started_at=started_at,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                next_scheduled_execution=next_scheduled_execution,
            )
            db.add(job_log)
            db.commit()
            db.refresh(job_log)
        except Exception as log_err:
            logger.warning("Could not persist initial job log for %s: %s", task_name, log_err)
            db.rollback()

    result = None
    failure_msg = None
    status = "SUCCESS"

    with SessionLocal() as db:
        try:
            result = task_fn(db, facility_id=facility_id)
            db.commit()
        except Exception as exc:
            db.rollback()
            status = "FAILED"
            failure_msg = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
            logger.error("Background task %s failed: %s", task_name, exc)
            raise exc
        finally:
            completed_at = datetime.now(timezone.utc)
            duration = (completed_at - started_at).total_seconds()
            if job_log:
                try:
                    with SessionLocal() as log_db:
                        record = log_db.get(BackgroundJobLog, job_log.id)
                        if record:
                            record.status = status
                            record.completed_at = completed_at
                            record.duration_seconds = duration
                            record.failure_message = failure_msg[:2000] if failure_msg else None
                            log_db.commit()
                except Exception as update_err:
                    logger.warning("Could not update final job log for %s: %s", task_name, update_err)

    return result
