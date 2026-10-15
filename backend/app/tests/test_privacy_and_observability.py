"""Integration tests for ODPC privacy compliance, health observability, and request correlation."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import Facility, Permission, Role, User
from app.models.privacy import DataBreach, DataSubjectRequest, ExportRequest, RetentionPolicy
from app.services.privacy import PrivacyService


@pytest.fixture
def privacy_setup(db: Session):
    facility = db.scalars(select(Facility)).first()

    # Create DPO user
    dpo_email = f"dpo_{uuid.uuid4().hex[:6]}@rehub.local"
    dpo = User(
        id=uuid.uuid4(),
        email=dpo_email,
        password_hash="argon2id$dpo_hash",
        full_name="Faith Mutua (Data Protection Officer)",
        facility_id=facility.id,
        active=True,
    )
    perm_codes = [
        "privacy.view",
        "privacy.manage",
        "privacy.dpo",
        "client.export",
        "clinical.export",
        "finance.export",
        "reports.export",
    ]
    for code in perm_codes:
        p = db.scalar(select(Permission).where(Permission.code == code))
        if not p:
            p = Permission(id=uuid.uuid4(), code=code, description=code)
            db.add(p)
        dpo.permissions.append(p)

    db.add(dpo)
    db.commit()
    return facility, dpo


def test_observability_health_endpoints(client):
    # Liveness probe
    resp_live = client.get("/health/live")
    assert resp_live.status_code == 200
    assert resp_live.json() == {"status": "live"}

    # Readiness probe
    resp_ready = client.get("/health/ready")
    assert resp_ready.status_code == 200
    data = resp_ready.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "healthy"

    # Correlation ID header injection and return
    req_id = "test-correlation-id-999"
    resp_corr = client.get("/health/live", headers={"X-Request-ID": req_id})
    assert resp_corr.headers.get("X-Request-ID") == req_id

    # System version endpoint
    resp_ver = client.get("/api/v1/system/version")
    assert resp_ver.status_code == 200
    ver_data = resp_ver.json()
    assert ver_data["version"] == "1.0.0"
    assert "ReHUB" in ver_data["name"]


def test_dsar_workflow_and_audit(db: Session, privacy_setup):
    facility, dpo = privacy_setup
    svc = PrivacyService(db, dpo)

    from app.schemas.privacy import DataSubjectRequestCreate, DataSubjectRequestReview

    # 1. Create DSAR
    create_in = DataSubjectRequestCreate(
        request_type="ACCESS",
        channel="WRITTEN",
        subject_name="David Kiprop",
        subject_contact="david@example.com",
        request_details="Request for full rehabilitation progress and medical summaries",
        verification_method="NATIONAL_ID",
    )
    dsar = svc.create_dsar(create_in)
    assert dsar.id is not None
    assert dsar.request_number.startswith("DSR-")
    assert dsar.status == "RECEIVED"

    # 2. Review and Fulfill DSAR
    review_in = DataSubjectRequestReview(
        status="FULFILLED",
        action_taken="Medical summaries printed and verified by Medical Officer",
        dpo_notes="Identity authenticated via national ID. Dispatched securely.",
    )
    updated = svc.review_dsar(dsar.id, review_in)
    assert updated.status == "FULFILLED"
    assert updated.fulfilled_at is not None
    assert updated.fulfilled_by == dpo.id


def test_data_breach_register_lifecycle(db: Session, privacy_setup):
    facility, dpo = privacy_setup
    svc = PrivacyService(db, dpo)

    from app.schemas.privacy import DataBreachCreate, DataBreachUpdate

    # 1. Log incident
    breach_in = DataBreachCreate(
        incident_date=datetime.now(timezone.utc),
        detected_date=datetime.now(timezone.utc),
        severity="HIGH",
        affected_categories=["CLINICAL_PROGRESS_NOTES"],
        estimated_affected_count=3,
        description="Printed progress notes left unattended in family conference area",
        containment_actions="Notes immediately retrieved and secured by Nurse on duty",
    )
    breach = svc.create_breach(breach_in)
    assert breach.incident_number.startswith("DB-")
    assert breach.status == "CONTAINED"

    # 2. Update with mitigation
    update_in = DataBreachUpdate(
        root_cause="Staff member exited room during urgent call",
        remedial_measures="Retraining on clear desk policy completed",
        odpc_notified=True,
        odpc_reference_number="ODPC/INC/2026/0442",
    )
    updated = svc.update_breach(breach.id, update_in)
    assert updated.odpc_notified is True
    assert updated.odpc_reference_number == "ODPC/INC/2026/0442"

    # 3. DPO formal signoff
    closed = svc.signoff_breach(breach.id, "Remedial measures inspected and verified. Case closed.")
    assert closed.status == "CLOSED"
    assert closed.dpo_signoff_by == dpo.id


def test_retention_policies_seeding(db: Session, privacy_setup):
    facility, dpo = privacy_setup
    svc = PrivacyService(db, dpo)

    policies = svc.seed_default_retention_policies()
    assert len(policies) >= 5
    types = {p.record_type for p in policies}
    assert "CLINICAL_ADMISSION" in types
    assert "FINANCIAL_LEDGER" in types
    assert "PHARMACY_DISPENSING" in types


def test_controlled_export_request_flow(db: Session, privacy_setup):
    facility, dpo = privacy_setup
    svc = PrivacyService(db, dpo)

    from app.schemas.privacy import ExportRequestApprove, ExportRequestCreate

    # 1. Request export
    exp_in = ExportRequestCreate(
        export_type="CLIENT_BULK",
        reason="Annual statutory Ministry of Health non-identifiable statistics reporting",
        format="CSV",
    )
    export_req = svc.request_export(exp_in)
    assert export_req.status == "PENDING_APPROVAL"
    assert export_req.requested_by == dpo.id

    # 2. DPO approves export
    appr_in = ExportRequestApprove(decision="APPROVE", notes="MOH request authorized by Board")
    approved = svc.approve_export(export_req.id, appr_in)
    assert approved.status == "APPROVED"
    assert approved.approved_by == dpo.id

    # 3. Download export payload
    content, media_type, filename = svc.download_export(export_req.id)
    assert media_type == "text/csv"
    assert "Client Number" in content
    assert filename.endswith(".csv")
    assert approved.download_count == 1
