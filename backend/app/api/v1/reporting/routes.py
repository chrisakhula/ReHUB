"""Reporting API routes."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.services.reporting import ReportingService
from app.schemas.reporting import DashboardMetricsOut, ReportParams, ReportResult


router = APIRouter(
    prefix="/reporting",
    tags=["Reporting"],
    dependencies=[Depends(require_permission("system.view"))]
)

@router.get("/dashboard", response_model=DashboardMetricsOut)
def get_dashboard_metrics(
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("system.view"))
):
    service = ReportingService(db, request, actor)
    return service.get_dashboard_metrics()

@router.post("/clinical", response_model=ReportResult)
def generate_clinical_report(
    request: Request,
    params: ReportParams,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("clinical.view"))
):
    service = ReportingService(db, request, actor)
    return service.generate_clinical_report(params.start_date, params.end_date)

@router.post("/financial", response_model=ReportResult)
def generate_financial_report(
    request: Request,
    params: ReportParams,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = ReportingService(db, request, actor)
    return service.generate_financial_report(params.start_date, params.end_date)
