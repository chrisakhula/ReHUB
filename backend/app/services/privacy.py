"""ODPC Privacy and Data Protection Service (Kenya Data Protection Act 2019).

Enforces statutory compliance for Data Subject Access Requests (DSAR), breach
registers, retention policies, and strictly audited bulk export gating.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.clients import Client
from app.models.identity import AuditEvent, User
from app.models.privacy import DataBreach, DataSubjectRequest, ExportRequest, RetentionPolicy
from app.schemas.privacy import (
    DataBreachCreate,
    DataBreachUpdate,
    DataSubjectRequestCreate,
    DataSubjectRequestReview,
    ExportRequestApprove,
    ExportRequestCreate,
    RetentionPolicyCreate,
)


class PrivacyService:
    def __init__(self, db: Session, actor: User):
        self.db = db
        self.actor = actor
        self.facility_id = actor.facility_id

    def _log_audit(self, action: str, entity: str, entity_id: str, new_values: dict = None, reason: str = None):
        audit = AuditEvent(
            id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            user_id=self.actor.id,
            facility_id=self.facility_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            new_values=new_values or {},
            reason=reason,
        )
        self.db.add(audit)

    # --- Data Subject Requests (DSAR) ---
    def create_dsar(self, data: DataSubjectRequestCreate) -> DataSubjectRequest:
        year = datetime.now(timezone.utc).year
        count = self.db.scalar(
            select(func.count(DataSubjectRequest.id)).where(DataSubjectRequest.facility_id == self.facility_id)
        ) or 0
        req_num = f"DSR-{year}-{count + 1:04d}"

        req = DataSubjectRequest(
            id=uuid.uuid4(),
            facility_id=self.facility_id,
            client_id=data.client_id,
            request_number=req_num,
            request_type=data.request_type,
            status="RECEIVED",
            channel=data.channel,
            subject_name=data.subject_name,
            subject_contact=data.subject_contact,
            request_details=data.request_details,
            verification_method=data.verification_method,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(req)
        self.db.flush()

        self._log_audit(
            action="privacy.dsar_created",
            entity="DataSubjectRequest",
            entity_id=str(req.id),
            new_values={"request_number": req_num, "request_type": data.request_type},
            reason="Subject exercised data protection rights under KDPA Section 26",
        )
        self.db.commit()
        return req

    def list_dsar(self, status: Optional[str] = None) -> List[DataSubjectRequest]:
        query = select(DataSubjectRequest).where(DataSubjectRequest.facility_id == self.facility_id)
        if status:
            query = query.where(DataSubjectRequest.status == status)
        query = query.order_by(desc(DataSubjectRequest.created_at))
        return list(self.db.scalars(query).all())

    def review_dsar(self, request_id: uuid.UUID, data: DataSubjectRequestReview) -> DataSubjectRequest:
        req = self.db.scalar(
            select(DataSubjectRequest).where(
                DataSubjectRequest.id == request_id,
                DataSubjectRequest.facility_id == self.facility_id,
            )
        )
        if not req:
            raise ValueError("Data Subject Request not found")

        req.status = data.status
        if data.dpo_notes:
            req.dpo_notes = data.dpo_notes
        if data.action_taken:
            req.action_taken = data.action_taken
        if data.rejection_reason:
            req.rejection_reason = data.rejection_reason

        if data.status == "FULFILLED":
            req.fulfilled_at = datetime.now(timezone.utc)
            req.fulfilled_by = self.actor.id

        req.updated_by = self.actor.id

        self._log_audit(
            action="privacy.dsar_reviewed",
            entity="DataSubjectRequest",
            entity_id=str(req.id),
            new_values={"status": data.status, "action_taken": data.action_taken},
            reason=data.dpo_notes or "DPO reviewed DSAR",
        )
        self.db.commit()
        return req

    # --- Data Breach Register ---
    def create_breach(self, data: DataBreachCreate) -> DataBreach:
        year = datetime.now(timezone.utc).year
        count = self.db.scalar(
            select(func.count(DataBreach.id)).where(DataBreach.facility_id == self.facility_id)
        ) or 0
        incident_num = f"DB-{year}-{count + 1:04d}"

        breach = DataBreach(
            id=uuid.uuid4(),
            facility_id=self.facility_id,
            incident_number=incident_num,
            incident_date=data.incident_date,
            detected_date=data.detected_date,
            severity=data.severity,
            affected_categories=data.affected_categories,
            estimated_affected_count=data.estimated_affected_count,
            description=data.description,
            containment_actions=data.containment_actions,
            status="CONTAINED",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(breach)
        self.db.flush()

        self._log_audit(
            action="privacy.breach_logged",
            entity="DataBreach",
            entity_id=str(breach.id),
            new_values={"incident_number": incident_num, "severity": data.severity},
            reason="Data incident logged in ODPC breach register",
        )
        self.db.commit()
        return breach

    def list_breaches(self) -> List[DataBreach]:
        query = (
            select(DataBreach)
            .where(DataBreach.facility_id == self.facility_id)
            .order_by(desc(DataBreach.detected_date))
        )
        return list(self.db.scalars(query).all())

    def update_breach(self, breach_id: uuid.UUID, data: DataBreachUpdate) -> DataBreach:
        breach = self.db.scalar(
            select(DataBreach).where(
                DataBreach.id == breach_id,
                DataBreach.facility_id == self.facility_id,
            )
        )
        if not breach:
            raise ValueError("Data breach incident not found")

        if data.root_cause is not None:
            breach.root_cause = data.root_cause
        if data.remedial_measures is not None:
            breach.remedial_measures = data.remedial_measures
        if data.containment_actions is not None:
            breach.containment_actions = data.containment_actions
        if data.odpc_notified is not None:
            breach.odpc_notified = data.odpc_notified
            if data.odpc_notified and not breach.odpc_notified_at:
                breach.odpc_notified_at = datetime.now(timezone.utc)
        if data.odpc_reference_number is not None:
            breach.odpc_reference_number = data.odpc_reference_number
        if data.data_subjects_notified is not None:
            breach.data_subjects_notified = data.data_subjects_notified
        if data.status is not None:
            breach.status = data.status

        breach.updated_by = self.actor.id
        self._log_audit(
            action="privacy.breach_updated",
            entity="DataBreach",
            entity_id=str(breach.id),
            new_values={"status": breach.status, "odpc_notified": breach.odpc_notified},
            reason="Breach containment and mitigation updated",
        )
        self.db.commit()
        return breach

    def signoff_breach(self, breach_id: uuid.UUID, notes: str) -> DataBreach:
        breach = self.db.scalar(
            select(DataBreach).where(
                DataBreach.id == breach_id,
                DataBreach.facility_id == self.facility_id,
            )
        )
        if not breach:
            raise ValueError("Data breach incident not found")

        breach.dpo_signoff_by = self.actor.id
        breach.dpo_signoff_at = datetime.now(timezone.utc)
        breach.status = "CLOSED"
        breach.updated_by = self.actor.id

        self._log_audit(
            action="privacy.breach_signed_off",
            entity="DataBreach",
            entity_id=str(breach.id),
            new_values={"status": "CLOSED", "dpo_signoff": str(self.actor.id)},
            reason=notes or "DPO formal incident closure",
        )
        self.db.commit()
        return breach

    # --- Retention Policies ---
    def list_retention_policies(self) -> List[RetentionPolicy]:
        return list(
            self.db.scalars(
                select(RetentionPolicy)
                .where(RetentionPolicy.facility_id == self.facility_id)
                .order_by(RetentionPolicy.record_type)
            ).all()
        )

    def seed_default_retention_policies(self) -> List[RetentionPolicy]:
        defaults = [
            (
                "CLINICAL_ADMISSION",
                10,
                "Kenya Health Act 2017 & KDPA 2019 Section 39",
                "Residential admission files, clinical assessments, vitals, doctor rounds",
            ),
            (
                "COUNSELLING_SESSION",
                10,
                "Counselors and Psychologists Act 2014 & KDPA 2019",
                "Psychotherapy progress notes, one-on-one and group therapy notes",
            ),
            (
                "PHARMACY_DISPENSING",
                7,
                "Pharmacy and Poisons Act Cap 244 & KDPA 2019",
                "Prescriptions, eMAR administration logs, controlled substance register",
            ),
            (
                "FINANCIAL_LEDGER",
                7,
                "Kenya Companies Act 2015 & Tax Procedures Act 2015",
                "General ledger, journal vouchers, invoice receipts, M-Pesa statements",
            ),
            (
                "STAFF_HR",
                6,
                "Employment Act 2007 Section 74 & KDPA 2019",
                "Staff personnel records, CPD certifications, professional registration licenses",
            ),
        ]
        created = []
        for rtype, years, legal, desc in defaults:
            exists = self.db.scalar(
                select(RetentionPolicy).where(
                    RetentionPolicy.facility_id == self.facility_id,
                    RetentionPolicy.record_type == rtype,
                )
            )
            if not exists:
                pol = RetentionPolicy(
                    id=uuid.uuid4(),
                    facility_id=self.facility_id,
                    record_type=rtype,
                    retention_period_years=years,
                    legal_basis=legal,
                    description=desc,
                    status="ACTIVE",
                    last_reviewed_at=datetime.now(timezone.utc),
                    created_by=self.actor.id,
                    updated_by=self.actor.id,
                )
                self.db.add(pol)
                created.append(pol)
        if created:
            self.db.commit()
        return self.list_retention_policies()

    # --- Controlled Export Workflows ---
    def request_export(self, data: ExportRequestCreate) -> ExportRequest:
        # Calculate estimated record count based on export type
        count = 0
        if data.export_type == "CLIENT_BULK":
            count = self.db.scalar(
                select(func.count(Client.id)).where(Client.facility_id == self.facility_id)
            ) or 0
        elif data.export_type == "FINANCE_BULK":
            count = 100  # Estimate
        else:
            count = 50

        exp = ExportRequest(
            id=uuid.uuid4(),
            facility_id=self.facility_id,
            export_type=data.export_type,
            filters=data.filters,
            record_count=count,
            reason=data.reason,
            format=data.format.upper(),
            requested_by=self.actor.id,
            status="PENDING_APPROVAL",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(exp)
        self.db.flush()

        self._log_audit(
            action="privacy.export_requested",
            entity="ExportRequest",
            entity_id=str(exp.id),
            new_values={"export_type": data.export_type, "record_count": count, "format": exp.format},
            reason=data.reason,
        )
        self.db.commit()
        return exp

    def list_exports(self) -> List[ExportRequest]:
        return list(
            self.db.scalars(
                select(ExportRequest)
                .where(ExportRequest.facility_id == self.facility_id)
                .order_by(desc(ExportRequest.created_at))
            ).all()
        )

    def approve_export(self, export_id: uuid.UUID, approval: ExportRequestApprove) -> ExportRequest:
        exp = self.db.scalar(
            select(ExportRequest).where(
                ExportRequest.id == export_id,
                ExportRequest.facility_id == self.facility_id,
            )
        )
        if not exp:
            raise ValueError("Export request not found")

        if approval.decision == "APPROVE":
            exp.status = "APPROVED"
            exp.approved_by = self.actor.id
            exp.approved_at = datetime.now(timezone.utc)
            action = "privacy.export_approved"
        else:
            exp.status = "REJECTED"
            action = "privacy.export_rejected"

        exp.updated_by = self.actor.id
        self._log_audit(
            action=action,
            entity="ExportRequest",
            entity_id=str(exp.id),
            new_values={"status": exp.status},
            reason=approval.notes or "DPO/Admin export decision",
        )
        self.db.commit()
        return exp

    def download_export(self, export_id: uuid.UUID) -> Tuple[str, str, str]:
        exp = self.db.scalar(
            select(ExportRequest).where(
                ExportRequest.id == export_id,
                ExportRequest.facility_id == self.facility_id,
            )
        )
        if not exp:
            raise ValueError("Export request not found")
        if exp.status != "APPROVED":
            raise ValueError(f"Export cannot be downloaded in status: {exp.status}")

        exp.download_count += 1
        exp.downloaded_at = datetime.now(timezone.utc)
        exp.updated_by = self.actor.id

        self._log_audit(
            action="privacy.export_downloaded",
            entity="ExportRequest",
            entity_id=str(exp.id),
            new_values={"download_count": exp.download_count},
            reason=f"Bulk data export downloaded by {self.actor.email}",
        )
        self.db.commit()

        # Generate CSV payload
        output = io.StringIO()
        writer = csv.writer(output)
        if exp.export_type == "CLIENT_BULK":
            clients = self.db.scalars(
                select(Client).where(Client.facility_id == self.facility_id)
            ).all()
            writer.writerow(["Client Number", "First Name", "Surname", "Sex", "National ID"])
            for c in clients:
                writer.writerow([c.client_number, c.first_name, c.surname, c.sex, c.national_id])
            filename = f"rehub_clients_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            writer.writerow(["Export Type", "Facility", "Generated At", "Record Count"])
            writer.writerow([exp.export_type, str(self.facility_id), datetime.now(timezone.utc).isoformat(), exp.record_count])
            filename = f"rehub_export_{exp.export_type.lower()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

        return output.getvalue(), "text/csv", filename
