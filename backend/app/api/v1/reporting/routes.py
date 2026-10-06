from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

from app.core.permissions import require_permission

router = APIRouter(
    prefix="/reporting",
    tags=["Reporting"],
    dependencies=[Depends(require_permission("system.view"))]
)
@router.get("/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    # In a real scenario, this would query various tables.
    # For now, we return 0 as placeholder since it's under development.
    return {
        "active_clients": 0,
        "current_occupancy": 0,
        "pending_discharges": 0,
        "recent_incidents": 0,
        "outstanding_invoices": 0
    }
