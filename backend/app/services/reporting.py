"""Reporting service layer."""

from datetime import datetime
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.audit.service import audit
from app.models.identity import User
from app.models.clients import Admission
from app.models.residential import Incident, ResidentMovement
from app.models.billing import Invoice
from app.models.discharge import DischargePlan
from app.models.staff import StaffShift


class ReportingService:
    def __init__(self, db: Session, request: Request, actor: User):
        self.db = db
        self.request = request
        self.actor = actor
        self.facility_id = self.actor.facility_id

    def event(self, action: str, details: str = ""):
        audit(self.db, self.request, action, "Report", self.actor, None)

    def get_dashboard_metrics(self) -> dict:
        # 1. Active Clients (Admissions that are ACTIVE)
        active_clients = self.db.query(Admission).filter(
            Admission.facility_id == self.facility_id,
            Admission.status == "ACTIVE"
        ).count()

        # 2. Current Occupancy (Same as active for now, unless we subtract leave)
        # For a true occupancy, we subtract people currently on leave/AWOL
        away_movements = self.db.query(ResidentMovement).filter(
            ResidentMovement.facility_id == self.facility_id,
            ResidentMovement.movement_type.in_(["LEAVE", "HOSPITAL", "TRANSFER", "AWOL"])
        ).distinct(ResidentMovement.admission_id).count() # This is a simplification; a real one checks latest movement
        
        current_occupancy = max(0, active_clients - away_movements)

        # 3. Pending Discharges
        pending_discharges = self.db.query(DischargePlan).filter(
            DischargePlan.facility_id == self.facility_id,
            DischargePlan.status.in_(["DRAFT", "PENDING_APPROVAL", "APPROVED"])
        ).count()

        # 4. Open Incidents
        open_incidents = self.db.query(Incident).filter(
            Incident.facility_id == self.facility_id,
            Incident.status.in_(["OPEN", "INVESTIGATING"])
        ).count()

        # 5. Outstanding Invoices
        # Sum of total_amount - amount_paid for all PARTIAL or UNPAID invoices
        result = self.db.execute(text(
            """
            SELECT SUM(total_amount - amount_paid)
            FROM billing_invoices
            WHERE facility_id = :facility_id AND status IN ('UNPAID', 'PARTIAL')
            """
        ), {"facility_id": self.facility_id}).scalar()
        outstanding_invoices = float(result) if result else 0.0

        # 6. Total Staff on Shift Today
        today = datetime.utcnow().date()
        total_staff_on_shift = self.db.query(StaffShift).filter(
            StaffShift.facility_id == self.facility_id,
            StaffShift.shift_date == today,
            StaffShift.attended == True
        ).count()

        self.event("report.dashboard_viewed")

        return {
            "active_clients": active_clients,
            "current_occupancy": current_occupancy,
            "pending_discharges": pending_discharges,
            "open_incidents": open_incidents,
            "outstanding_invoices": outstanding_invoices,
            "total_staff_on_shift": total_staff_on_shift
        }

    def generate_clinical_report(self, start_date: str = None, end_date: str = None) -> dict:
        self.event("report.clinical_generated")
        # Placeholder for complex clinical report
        return {
            "report_name": "Clinical Overview",
            "columns": ["Admission ID", "Status", "Date"],
            "rows": []
        }

    def generate_financial_report(self, start_date: str = None, end_date: str = None) -> dict:
        self.event("report.financial_generated")
        # Placeholder for complex financial report
        return {
            "report_name": "Financial Overview",
            "columns": ["Invoice Number", "Amount", "Status"],
            "rows": []
        }
