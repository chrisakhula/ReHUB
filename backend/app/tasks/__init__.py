"""Background task modules package."""

from app.tasks.aftercare import process_aftercare_milestones_task
from app.tasks.clinical import detect_overdue_risk_reviews_task, escalate_critical_alerts_task
from app.tasks.compliance import check_compliance_expiry_task
from app.tasks.finance import check_overdue_invoices_task
from app.tasks.medication import detect_overdue_medications_task, generate_emar_rounds_task
from app.tasks.pharmacy import check_pharmacy_batches_task
from app.tasks.staff import check_staff_licence_expiry_task

__all__ = [
    "generate_emar_rounds_task",
    "detect_overdue_medications_task",
    "check_compliance_expiry_task",
    "process_aftercare_milestones_task",
    "escalate_critical_alerts_task",
    "detect_overdue_risk_reviews_task",
    "check_pharmacy_batches_task",
    "check_staff_licence_expiry_task",
    "check_overdue_invoices_task",
]
