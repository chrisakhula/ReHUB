"""Celery application and Celery Beat scheduled task configuration for ReHUB."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rehub",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.medication",
        "app.tasks.compliance",
        "app.tasks.aftercare",
        "app.tasks.clinical",
        "app.tasks.pharmacy",
        "app.tasks.staff",
        "app.tasks.finance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max hard timeout
    task_soft_time_limit=300,  # 5 minutes soft timeout
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        # Medication: Generate eMAR rounds every 4 hours
        "generate_emar_rounds_schedule": {
            "task": "app.tasks.medication.generate_emar_rounds_task",
            "schedule": crontab(minute=0, hour="*/4"),
        },
        # Medication: Detect overdue doses every 15 minutes
        "detect_overdue_medications_schedule": {
            "task": "app.tasks.medication.detect_overdue_medications_task",
            "schedule": crontab(minute="*/15"),
        },
        # Clinical: Escalate unacknowledged crisis alerts every 2 minutes
        "escalate_crisis_alerts_schedule": {
            "task": "app.tasks.clinical.escalate_critical_alerts_task",
            "schedule": crontab(minute="*/2"),
        },
        # Clinical: Detect overdue risk reviews daily at 06:00
        "detect_overdue_risk_reviews_schedule": {
            "task": "app.tasks.clinical.detect_overdue_risk_reviews_task",
            "schedule": crontab(minute=0, hour=6),
        },
        # Compliance: Scan statutory licences and expiry alerts daily at 07:00
        "compliance_expiry_scanner_schedule": {
            "task": "app.tasks.compliance.check_compliance_expiry_task",
            "schedule": crontab(minute=0, hour=7),
        },
        # Aftercare: Scan recovery follow-up milestones daily at 08:00
        "aftercare_milestone_scanner_schedule": {
            "task": "app.tasks.aftercare.process_aftercare_milestones_task",
            "schedule": crontab(minute=0, hour=8),
        },
        # Pharmacy: Scan expiring and low stock batches daily at 05:00
        "pharmacy_batch_and_stock_schedule": {
            "task": "app.tasks.pharmacy.check_pharmacy_batches_task",
            "schedule": crontab(minute=0, hour=5),
        },
        # Staff: Scan professional licences and training expiry daily at 07:30
        "staff_licence_expiry_schedule": {
            "task": "app.tasks.staff.check_staff_licence_expiry_task",
            "schedule": crontab(minute=30, hour=7),
        },
        # Finance: Check overdue invoices and reconciliation queues daily at 09:00
        "finance_overdue_and_reconciliation_schedule": {
            "task": "app.tasks.finance.check_overdue_invoices_task",
            "schedule": crontab(minute=0, hour=9),
        },
    },
)
