"""Clinical crisis detection, safe keyword scanning, escalation policy, and alert lifecycle."""

from datetime import datetime, timezone
import logging
import random
import re
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.clinical import CrisisAlert, CrisisEscalationPolicy
from app.models.identity import User
from app.notifications.sms import SmsNotificationService
from app.notifications.email import EmailNotificationService
from app.notifications.in_app import InAppNotificationService

logger = logging.getLogger("rehub.clinical.crisis")

# Explicit primary crisis indicators
CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die",
    "better off dead", "can't take this anymore", "hurt myself",
    "overdose", "cut myself", "give up on life", "kill himself", "kill herself"
]

# Negation patterns to prevent false-positive diagnostic classification
NEGATION_PATTERNS = [
    r"denies\s+(?:any\s+)?(?:thoughts\s+of\s+)?(?:suicid|wanting\s+to\s+(?:die|kill|harm)|harm|kill|death)",
    r"no\s+(?:active\s+|passive\s+)?(?:suicid|intent|ideation|plan|thoughts\s+of\s+harm)",
    r"denied\s+(?:any\s+)?(?:suicid|intent|harm|wanting\s+to\s+(?:die|kill))",
    r"not\s+(?:suicidal|wanting\s+to\s+(?:die|kill)|planning\s+to)",
    r"without\s+(?:suicid|intent|plan)",
    r"free\s+of\s+(?:suicid|ideation)",
]


def generate_crisis_reference(db: Session) -> str:
    """Generate sequential or formatted institutional crisis reference: CR-YYYY-NNNNNN."""
    year = datetime.now(timezone.utc).year
    # Count alerts in the current year
    count = db.scalar(
        select(func.count(CrisisAlert.id)).filter(
            CrisisAlert.created_at >= datetime(year, 1, 1, tzinfo=timezone.utc)
        )
    ) or 0
    seq = count + 1
    # Try formatted reference, ensuring uniqueness
    while True:
        ref = f"CR-{year}-{seq:06d}"
        exists = db.scalar(select(CrisisAlert.id).filter(CrisisAlert.alert_reference == ref))
        if not exists:
            return ref
        seq += 1


def is_negated_clinical_context(text: str) -> bool:
    """Detect if clinical notes specifically deny or rule out acute crisis risk."""
    text_lower = text.lower()
    for neg_regex in NEGATION_PATTERNS:
        if re.search(neg_regex, text_lower):
            return True
    return False


def scan_text_for_crisis(
    text: str,
    db: Session = None,
    facility_id: UUID = None,
    client_id: Optional[UUID] = None,
    admission_id: Optional[UUID] = None,
    source_entity: str = "ClinicalNote",
    source_entity_id: str = "Unknown",
    assigned_clinician_id: Optional[UUID] = None,
) -> List[str]:
    """
    Scans text as a SECONDARY signal.
    Safety rule: Never classifies suicide risk solely from keywords.
    Keyword detection produces 'REVIEW_REQUIRED' rather than a definitive diagnosis.
    Accounts for negation clauses (e.g. 'Client denies wanting to kill himself').
    """
    if not text:
        return []

    text_lower = text.lower()
    matches = []

    for keyword in CRISIS_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, text_lower):
            matches.append(keyword)

    if not matches:
        return []

    # Check for clinical negation
    is_negated = is_negated_clinical_context(text)
    if is_negated:
        logger.info(
            f"Crisis keywords {matches} identified in text but clinical negation was detected. Flagging for non-emergency review."
        )

    severity = "REVIEW_REQUIRED"
    status = "DETECTED"
    trigger = "KEYWORD_SCANNER_NEGATED" if is_negated else "KEYWORD_SCANNER"

    if db and facility_id:
        alert_ref = generate_crisis_reference(db)
        alert = CrisisAlert(
            facility_id=facility_id,
            client_id=client_id,
            admission_id=admission_id,
            alert_reference=alert_ref,
            source_entity=source_entity,
            source_entity_id=source_entity_id,
            trigger=trigger,
            detected_keywords=", ".join(matches),
            text_snippet=text[:500],
            severity=severity,
            status=status,
            assigned_clinician_id=assigned_clinician_id,
            escalation_level=0,
            escalation_history=[{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "DETECTED_BY_SCANNER",
                "negated": is_negated,
                "keywords": matches,
            }],
        )
        db.add(alert)

    return matches


class CrisisEscalationService:
    """Manages full lifecycle and policy escalation of clinical crises."""

    def __init__(
        self,
        sms_service: SmsNotificationService | None = None,
        email_service: EmailNotificationService | None = None,
        in_app_service: InAppNotificationService | None = None,
    ):
        self.sms_service = sms_service or SmsNotificationService()
        self.email_service = email_service or EmailNotificationService()
        self.in_app_service = in_app_service or InAppNotificationService()

    async def create_crisis_alert(
        self,
        db: Session,
        facility_id: UUID,
        client_id: UUID,
        admission_id: UUID | None,
        trigger: str,
        severity: str,
        source_entity: str,
        source_entity_id: str,
        text_snippet: str,
        assigned_clinician_id: UUID | None = None,
    ) -> CrisisAlert:
        """Create a validated assessment crisis alert and dispatch immediate tier-0 alerts."""
        alert_ref = generate_crisis_reference(db)
        alert = CrisisAlert(
            facility_id=facility_id,
            client_id=client_id,
            admission_id=admission_id,
            alert_reference=alert_ref,
            source_entity=source_entity,
            source_entity_id=source_entity_id,
            trigger=trigger,
            detected_keywords=trigger,
            text_snippet=text_snippet[:500],
            severity=severity,
            status="NEW",
            assigned_clinician_id=assigned_clinician_id,
            escalation_level=0,
            escalation_history=[{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "ALERT_CREATED",
                "severity": severity,
                "trigger": trigger,
            }],
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        # Immediate tier-0 dispatch
        await self._dispatch_initial_notification(db, alert)
        return alert

    async def _dispatch_initial_notification(self, db: Session, alert: CrisisAlert) -> None:
        """Dispatches immediate notification to assigned clinician or duty roster."""
        clinician: User | None = None
        if alert.assigned_clinician_id:
            clinician = db.get(User, alert.assigned_clinician_id)

        target_phone = getattr(clinician, "phone", None) if clinician else None
        target_email = getattr(clinician, "email", None) if clinician else None

        # In-app broadcast
        await self.in_app_service.broadcast_crisis_alert(
            facility_id=alert.facility_id,
            alert_id=alert.id,
            alert_reference=alert.alert_reference or "CR-ALERT",
            severity=alert.severity,
            trigger=alert.trigger,
            target_user_ids=[alert.assigned_clinician_id] if alert.assigned_clinician_id else [],
        )

        # SMS broadcast (Privacy rule: no sensitive clinical details, only reference and login request)
        if target_phone:
            await self.sms_service.send_crisis_alert_sms(
                phone_number=target_phone,
                alert_reference=alert.alert_reference or "CR-ALERT",
                urgency=alert.severity,
            )

        if target_email:
            await self.email_service.send_crisis_alert_email(
                recipient_email=target_email,
                alert_reference=alert.alert_reference or "CR-ALERT",
                severity=alert.severity,
                trigger=alert.trigger,
                recipient_name=getattr(clinician, "full_name", "Duty Clinician"),
            )

    def acknowledge_alert(
        self,
        db: Session,
        alert_id: UUID,
        user_id: UUID,
        note: str = "",
    ) -> CrisisAlert:
        """Acknowledge alert: changes status to ACKNOWLEDGED, halting escalation timers."""
        alert = db.get(CrisisAlert, alert_id)
        if not alert:
            raise ValueError(f"Crisis alert {alert_id} not found.")

        now = datetime.now(timezone.utc)
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = user_id
        alert.acknowledged_at = now
        
        history = list(alert.escalation_history or [])
        history.append({
            "timestamp": now.isoformat(),
            "action": "ACKNOWLEDGED",
            "user_id": str(user_id),
            "note": note,
        })
        alert.escalation_history = history

        db.commit()
        db.refresh(alert)
        return alert

    def start_review(
        self,
        db: Session,
        alert_id: UUID,
        user_id: UUID,
        response_summary: str,
        intervention_plan: str,
    ) -> CrisisAlert:
        """Move alert into UNDER_REVIEW with documented clinician response and safety intervention."""
        alert = db.get(CrisisAlert, alert_id)
        if not alert:
            raise ValueError(f"Crisis alert {alert_id} not found.")

        now = datetime.now(timezone.utc)
        alert.status = "UNDER_REVIEW"
        alert.response = response_summary
        alert.intervention = intervention_plan

        history = list(alert.escalation_history or [])
        history.append({
            "timestamp": now.isoformat(),
            "action": "UNDER_REVIEW",
            "user_id": str(user_id),
            "response": response_summary,
            "intervention": intervention_plan,
        })
        alert.escalation_history = history

        db.commit()
        db.refresh(alert)
        return alert

    def resolve_alert(
        self,
        db: Session,
        alert_id: UUID,
        user_id: UUID,
        resolution_notes: str,
    ) -> CrisisAlert:
        """Resolve crisis alert with definitive clinical disposition."""
        alert = db.get(CrisisAlert, alert_id)
        if not alert:
            raise ValueError(f"Crisis alert {alert_id} not found.")

        now = datetime.now(timezone.utc)
        alert.status = "RESOLVED"
        alert.resolution = resolution_notes
        alert.resolved_by_id = user_id
        alert.resolved_at = now

        history = list(alert.escalation_history or [])
        history.append({
            "timestamp": now.isoformat(),
            "action": "RESOLVED",
            "user_id": str(user_id),
            "resolution": resolution_notes,
        })
        alert.escalation_history = history

        db.commit()
        db.refresh(alert)
        return alert

    async def evaluate_escalations(self, db: Session) -> int:
        """
        Background policy engine:
        Scans all active unacknowledged CRITICAL alerts.
        Applies configurable facility escalation policies:
        Tier 1 (e.g. 5 min unacknowledged) -> Escalates to Duty Clinician
        Tier 2 (e.g. 10 min unacknowledged) -> Escalates to Clinical Manager / Medical Director
        """
        now = datetime.now(timezone.utc)
        # Find unacknowledged high/critical alerts
        open_alerts = db.scalars(
            select(CrisisAlert).filter(
                CrisisAlert.status.in_(["NEW", "DETECTED", "ESCALATED"]),
                CrisisAlert.severity.in_(["CRITICAL", "HIGH"]),
            )
        ).all()

        escalated_count = 0

        for alert in open_alerts:
            # Get policy for facility
            policy = db.scalars(
                select(CrisisEscalationPolicy).filter(
                    CrisisEscalationPolicy.facility_id == alert.facility_id,
                    CrisisEscalationPolicy.severity == alert.severity,
                )
            ).first()

            tier_1_mins = policy.tier_1_delay_minutes if policy else 5
            tier_2_mins = policy.tier_2_delay_minutes if policy else 10

            created_time = alert.created_at
            if created_time.tzinfo is None:
                created_time = created_time.replace(tzinfo=timezone.utc)

            elapsed_minutes = (now - created_time).total_seconds() / 60.0

            history = list(alert.escalation_history or [])

            # Check Tier 2 escalation
            if elapsed_minutes >= tier_2_mins and alert.escalation_level < 2:
                alert.escalation_level = 2
                alert.status = "ESCALATED"
                entry = {
                    "timestamp": now.isoformat(),
                    "action": "TIER_2_ESCALATION",
                    "reason": f"Unacknowledged after {int(elapsed_minutes)} minutes (threshold: {tier_2_mins}m)",
                    "target_role": "Clinical Manager / Medical Director",
                }
                history.append(entry)
                alert.escalation_history = history
                escalated_count += 1
                logger.warning(
                    f"CRITICAL CRISIS ESCALATED TO TIER 2: Alert {alert.alert_reference} unacknowledged for {int(elapsed_minutes)}m."
                )

                # Broadcast tier-2 emergency SMS
                if policy is None or policy.notify_sms:
                    # Look up duty manager / clinical leadership for facility
                    manager = db.scalars(
                        select(User).filter(
                            User.facility_id == alert.facility_id,
                            User.active.is_(True),
                        )
                    ).first()
                    if manager and manager.phone:
                        await self.sms_service.send_crisis_alert_sms(
                            phone_number=manager.phone,
                            alert_reference=alert.alert_reference or "CR-ALERT",
                            urgency="ESCALATED_CRITICAL",
                        )

            # Check Tier 1 escalation
            elif elapsed_minutes >= tier_1_mins and alert.escalation_level < 1:
                alert.escalation_level = 1
                alert.status = "ESCALATED"
                entry = {
                    "timestamp": now.isoformat(),
                    "action": "TIER_1_ESCALATION",
                    "reason": f"Unacknowledged after {int(elapsed_minutes)} minutes (threshold: {tier_1_mins}m)",
                    "target_role": "Duty Clinician",
                }
                history.append(entry)
                alert.escalation_history = history
                escalated_count += 1
                logger.warning(
                    f"CRITICAL CRISIS ESCALATED TO TIER 1: Alert {alert.alert_reference} unacknowledged for {int(elapsed_minutes)}m."
                )

        if escalated_count > 0:
            db.commit()

        return escalated_count


# Singleton for shared access
crisis_escalation_service = CrisisEscalationService()
