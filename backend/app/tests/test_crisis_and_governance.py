"""Automated test suite for Sprint C: Clinical Crisis Escalation & Clinical Governance."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clinical import CrisisAlert, CrisisEscalationPolicy
from app.models.clinical_governance import (
    ClinicalApproval,
    ClinicalConfiguration,
    ClinicalConfigurationVersion,
)
from app.models.identity import Facility, User
from app.notifications.sms import SmsNotificationService
from app.notifications.providers.mock import MockNotificationProvider
from app.services.clinical_governance import clinical_governance_service
from app.services.crisis import (
    CrisisEscalationService,
    is_negated_clinical_context,
    scan_text_for_crisis,
)


@pytest.fixture
def facility_and_user(db: Session):
    fac = db.scalars(select(Facility)).first()

    user = User(
        id=uuid4(),
        email="doctor@serenity.org",
        password_hash="argon2id$mockhash",
        full_name="Dr. Jane Kamau",
        facility_id=fac.id,
        active=True,
    )
    db.add(user)
    db.commit()
    return fac, user


def test_keyword_scanner_negation_safety(db: Session, facility_and_user):
    fac, user = facility_and_user

    # Negation statement: client explicitly denies suicidality
    negated_text = "Client presented calm and denies wanting to kill himself or any thoughts of harm."
    assert is_negated_clinical_context(negated_text) is True

    matches = scan_text_for_crisis(
        text=negated_text,
        db=db,
        facility_id=fac.id,
        source_entity="ClinicalNote",
    )
    db.commit()

    assert "kill himself" in matches
    # Verify the created alert is marked as secondary review, NOT a definitive diagnosis
    alert = db.scalars(
        select(CrisisAlert).filter(CrisisAlert.facility_id == fac.id)
    ).first()
    assert alert is not None
    assert alert.severity == "REVIEW_REQUIRED"
    assert alert.trigger == "KEYWORD_SCANNER_NEGATED"
    assert alert.status == "DETECTED"
    assert alert.alert_reference.startswith("CR-")


def test_sms_privacy_sanitization():
    mock_prov = MockNotificationProvider()
    sms_service = SmsNotificationService(provider=mock_prov)

    # Attempt to send text containing sensitive terms
    sensitive_msg = "Client John Doe admitted with severe depression and active suicide plan using heroin."
    sanitized = sms_service.sanitize_message(sensitive_msg, alert_reference="CR-2026-000042")

    # The sanitized message must NOT leak diagnostic or suicidal terms
    assert "suicide" not in sanitized.lower()
    assert "depression" not in sanitized.lower()
    assert "heroin" not in sanitized.lower()
    assert "CR-2026-000042" in sanitized
    assert "Please sign in to the secure institutional portal" in sanitized


def test_crisis_escalation_lifecycle(db: Session, facility_and_user):
    fac, user = facility_and_user
    mock_prov = MockNotificationProvider()
    escalation_service = CrisisEscalationService(
        sms_service=SmsNotificationService(provider=mock_prov)
    )

    # 1. Create alert from validated tool
    alert = asyncio.run(
        escalation_service.create_crisis_alert(
            db=db,
            facility_id=fac.id,
            client_id=None,
            admission_id=None,
            trigger="ASSESSMENT_CSSRS_HIGH",
            severity="CRITICAL",
            source_entity="Assessment",
            source_entity_id="CSSRS-1",
            text_snippet="Active ideation with intent and specific plan.",
            assigned_clinician_id=user.id,
        )
    )
    assert alert.status == "NEW"
    assert alert.severity == "CRITICAL"
    assert alert.alert_reference.startswith("CR-")

    # 2. Acknowledge alert
    alert = escalation_service.acknowledge_alert(
        db=db,
        alert_id=alert.id,
        user_id=user.id,
        note="Duty clinician on site",
    )
    assert alert.status == "ACKNOWLEDGED"
    assert alert.acknowledged_by == user.id

    # 3. Start review & safety intervention
    alert = escalation_service.start_review(
        db=db,
        alert_id=alert.id,
        user_id=user.id,
        response_summary="Client assessed in quiet room with nursing sister.",
        intervention_plan="Placed on 1:1 continuous nursing observation.",
    )
    assert alert.status == "UNDER_REVIEW"
    assert alert.response == "Client assessed in quiet room with nursing sister."

    # 4. Resolve crisis
    alert = escalation_service.resolve_alert(
        db=db,
        alert_id=alert.id,
        user_id=user.id,
        resolution_notes="Stabilized, transferred to low-stimulation ward.",
    )
    assert alert.status == "RESOLVED"
    assert alert.resolved_by_id == user.id
    assert alert.resolved_at is not None


def test_crisis_policy_engine_escalation(db: Session, facility_and_user):
    fac, user = facility_and_user
    mock_prov = MockNotificationProvider()
    escalation_service = CrisisEscalationService(
        sms_service=SmsNotificationService(provider=mock_prov)
    )

    # Setup policy with 5m and 10m thresholds
    policy = CrisisEscalationPolicy(
        facility_id=fac.id,
        severity="CRITICAL",
        tier_1_delay_minutes=5,
        tier_2_delay_minutes=10,
        notify_sms=True,
    )
    db.add(policy)

    # Create unacknowledged alert backdated 6 minutes ago (should trigger Tier 1)
    now = datetime.now(timezone.utc)
    alert = CrisisAlert(
        facility_id=fac.id,
        alert_reference="CR-2026-999999",
        source_entity="Assessment",
        source_entity_id="test",
        trigger="TEST_CRITICAL",
        detected_keywords="severe risk",
        text_snippet="Test unacknowledged snippet",
        severity="CRITICAL",
        status="NEW",
        escalation_level=0,
        created_at=now - timedelta(minutes=6),
    )
    db.add(alert)
    db.commit()

    # Evaluate escalations
    escalated = asyncio.run(escalation_service.evaluate_escalations(db))
    assert escalated == 1

    db.refresh(alert)
    assert alert.escalation_level == 1
    assert alert.status == "ESCALATED"
    assert any(h.get("action") == "TIER_1_ESCALATION" for h in alert.escalation_history)


def test_clinical_configuration_governance(db: Session, facility_and_user):
    fac, user = facility_and_user

    # 1. Seed baseline configurations
    seeded_count = clinical_governance_service.seed_baseline_configurations(
        db=db,
        facility_id=fac.id,
        created_by_id=user.id,
    )
    assert seeded_count >= 5

    # Verify AUDIT configuration exists and is PENDING_APPROVAL
    audit_cfg = clinical_governance_service.get_configuration_by_key(db, fac.id, "AUDIT")
    assert audit_cfg is not None
    assert audit_cfg.current_version_id is not None

    version = db.get(ClinicalConfigurationVersion, audit_cfg.current_version_id)
    assert version.status == "PENDING_APPROVAL"

    # Golden rule test: Before approval, version must NOT be marked APPROVED
    assert version.status != "APPROVED"

    # 2. Institutional sign-off by Medical Director with KMPDC credentials
    approval = clinical_governance_service.approve_version(
        db=db,
        version_id=version.id,
        approver_id=user.id,
        approver_name="Dr. Jane Kamau",
        professional_designation="Medical Director / Consultant Psychiatrist",
        professional_registration="KMPDC Reg. No. A-14289",
        notes="Institutional validation of standard WHO AUDIT cutoffs.",
    )

    assert approval.status == "APPROVED"
    assert approval.professional_registration == "KMPDC Reg. No. A-14289"

    db.refresh(version)
    assert version.status == "APPROVED"

    # Verify get_effective_version returns the approved version
    effective = clinical_governance_service.get_effective_version(db, fac.id, "AUDIT")
    assert effective is not None
    assert effective.id == version.id
