from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/reporting", tags=["Reporting"])

@router.get("/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    # In a real scenario, this would query various tables.
    # For now, we return placeholder structure matching the requirements.
    return {
        "active_clients": 42,
        "current_occupancy": 85,
        "pending_discharges": 3,
        "recent_incidents": 1,
        "outstanding_invoices": 12
    }
