"""Reporting schemas."""

from typing import Dict, Any, List
from pydantic import BaseModel


class DashboardMetricsOut(BaseModel):
    active_clients: int
    current_occupancy: int
    pending_discharges: int
    open_incidents: int
    outstanding_invoices: float
    total_staff_on_shift: int


class ReportParams(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    group_by: str | None = None


class ReportResult(BaseModel):
    report_name: str
    columns: List[str]
    rows: List[Dict[str, Any]]
