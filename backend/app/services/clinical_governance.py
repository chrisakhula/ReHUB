"""Clinical configuration governance service: versioning, approval workflows, and threshold enforcement."""

from datetime import date, datetime, timezone
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clinical_governance import (
    ClinicalApproval,
    ClinicalConfiguration,
    ClinicalConfigurationVersion,
)

logger = logging.getLogger("rehub.clinical.governance")

# Standard clinical instrument catalog
DEFAULT_INSTRUMENTS = [
    {
        "key": "AUDIT",
        "name": "Alcohol Use Disorders Identification Test",
        "category": "ASSESSMENT",
        "description": "WHO 10-item screening tool for hazardous and harmful alcohol consumption.",
        "source_reference": "WHO Guidelines on Identification and Management of Substance Use Disorders",
        "schema_definition": {
            "scale": "0-40",
            "cutoffs": {
                "low_risk": {"min": 0, "max": 7, "action": "Brief education"},
                "hazardous_drinking": {"min": 8, "max": 15, "action": "Brief advice, counseling"},
                "harmful_drinking": {"min": 16, "max": 19, "action": "Brief counseling and monitoring"},
                "alcohol_dependence": {"min": 20, "max": 40, "action": "Referral to specialist / residential detox"},
            },
        },
    },
    {
        "key": "PHQ9",
        "name": "Patient Health Questionnaire (PHQ-9)",
        "category": "ASSESSMENT",
        "description": "Validated 9-item depression severity and suicide ideation assessment.",
        "source_reference": "Kroenke et al., Journal of General Internal Medicine 2001",
        "schema_definition": {
            "scale": "0-27",
            "cutoffs": {
                "minimal": {"min": 0, "max": 4},
                "mild": {"min": 5, "max": 9},
                "moderate": {"min": 10, "max": 14},
                "moderately_severe": {"min": 15, "max": 19},
                "severe": {"min": 20, "max": 27},
            },
            "critical_rules": [
                {"question_index": 9, "threshold": 1, "trigger": "CRITICAL_SUICIDE_RISK_ALERT"}
            ],
        },
    },
    {
        "key": "GAD7",
        "name": "Generalized Anxiety Disorder 7-item Scale",
        "category": "ASSESSMENT",
        "description": "Self-report scale for diagnosing and assessing the severity of generalized anxiety disorder.",
        "source_reference": "Spitzer et al., Archives of Internal Medicine 2006",
        "schema_definition": {
            "scale": "0-21",
            "cutoffs": {
                "minimal": {"min": 0, "max": 4},
                "mild": {"min": 5, "max": 9},
                "moderate": {"min": 10, "max": 14},
                "severe": {"min": 15, "max": 21},
            },
        },
    },
    {
        "key": "CSSRS",
        "name": "Columbia-Suicide Severity Rating Scale",
        "category": "ESCALATION",
        "description": "Standardized suicide risk assessment tracking suicidal ideation and suicidal behaviour.",
        "source_reference": "Posner et al., American Journal of Psychiatry 2011",
        "schema_definition": {
            "risk_tiers": {
                "low": {"criteria": "Wish to be dead or non-specific suicidal thoughts (Q1, Q2)", "action": "Standard observation"},
                "moderate": {"criteria": "Active suicidal ideation without intent/plan (Q3)", "action": "Increased observation, urgent review"},
                "high": {"criteria": "Active ideation with intent and/or plan, or suicidal behavior (Q4, Q5, or preparatory acts)", "action": "Immediate 1:1 observation, Medical Director emergency alert"},
            }
        },
    },
    {
        "key": "CIWA_AR",
        "name": "Clinical Institute Withdrawal Assessment for Alcohol (Revised)",
        "category": "WITHDRAWAL",
        "description": "10-item instrument for monitoring alcohol withdrawal symptom severity.",
        "source_reference": "Sullivan et al., British Journal of Addiction 1989",
        "schema_definition": {
            "scale": "0-67",
            "cutoffs": {
                "mild": {"min": 0, "max": 9, "protocol": "Supportive care, reassess every 8 hours"},
                "moderate": {"min": 10, "max": 19, "protocol": "Medication indicated (Diazepam titration), reassess every 2-4 hours"},
                "severe": {"min": 20, "max": 67, "protocol": "Urgent Medical Officer review, intensive nursing, aggressive detox"},
            },
        },
    },
    {
        "key": "COWS",
        "name": "Clinical Opiate Withdrawal Scale",
        "category": "WITHDRAWAL",
        "description": "11-item scale to assess symptoms and severity of opiate withdrawal.",
        "source_reference": "Wesson & Ling, Journal of Psychoactive Drugs 2003",
        "schema_definition": {
            "scale": "0-48",
            "cutoffs": {
                "mild": {"min": 5, "max": 12},
                "moderate": {"min": 13, "max": 24},
                "moderately_severe": {"min": 25, "max": 36},
                "severe": {"min": 37, "max": 48},
            },
        },
    },
]


class ClinicalGovernanceService:
    """Manages institutional governance, versioning, and approvals for clinical tools."""

    def list_configurations(
        self, db: Session, facility_id: UUID, category: str | None = None
    ) -> list[ClinicalConfiguration]:
        query = select(ClinicalConfiguration).filter(ClinicalConfiguration.facility_id == facility_id)
        if category:
            query = query.filter(ClinicalConfiguration.category == category)
        return list(db.scalars(query.order_by(ClinicalConfiguration.name)).all())

    def get_configuration_by_key(
        self, db: Session, facility_id: UUID, key: str
    ) -> ClinicalConfiguration | None:
        return db.scalars(
            select(ClinicalConfiguration).filter(
                ClinicalConfiguration.facility_id == facility_id,
                ClinicalConfiguration.key == key.upper(),
            )
        ).first()

    def get_effective_version(
        self, db: Session, facility_id: UUID, key: str
    ) -> ClinicalConfigurationVersion | None:
        """Retrieves the active, institutionally approved version for an instrument."""
        config = self.get_configuration_by_key(db, facility_id, key)
        if not config or not config.current_version_id:
            return None
        return db.get(ClinicalConfigurationVersion, config.current_version_id)

    def create_draft_version(
        self,
        db: Session,
        configuration_id: UUID,
        schema_definition: dict[str, Any],
        source_reference: str,
        effective_date: date,
        review_date: date,
        user_id: UUID,
    ) -> ClinicalConfigurationVersion:
        """Creates a new draft version under an existing instrument configuration."""
        config = db.get(ClinicalConfiguration, configuration_id)
        if not config:
            raise ValueError(f"ClinicalConfiguration {configuration_id} not found.")

        # Determine next version number
        latest_v = db.scalars(
            select(ClinicalConfigurationVersion.version_number)
            .filter(ClinicalConfigurationVersion.configuration_id == configuration_id)
            .order_by(ClinicalConfigurationVersion.version_number.desc())
        ).first() or 0

        version = ClinicalConfigurationVersion(
            configuration_id=configuration_id,
            version_number=latest_v + 1,
            source_reference=source_reference,
            schema_definition=schema_definition,
            effective_date=effective_date,
            review_date=review_date,
            status="DRAFT",
            created_by=user_id,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    def submit_for_approval(
        self, db: Session, version_id: UUID
    ) -> ClinicalConfigurationVersion:
        version = db.get(ClinicalConfigurationVersion, version_id)
        if not version:
            raise ValueError("Configuration version not found.")
        if version.status != "DRAFT":
            raise ValueError(f"Cannot submit version with status {version.status}.")

        version.status = "PENDING_APPROVAL"
        db.commit()
        db.refresh(version)
        return version

    def approve_version(
        self,
        db: Session,
        version_id: UUID,
        approver_id: UUID,
        approver_name: str,
        professional_designation: str,
        professional_registration: str,
        notes: str = "",
    ) -> ClinicalApproval:
        """
        Formally approves a clinical instrument version with statutory registration details.
        Activates the version as current and retires previous versions.
        """
        version = db.get(ClinicalConfigurationVersion, version_id)
        if not version:
            raise ValueError("Configuration version not found.")
        if version.status not in ("DRAFT", "PENDING_APPROVAL"):
            raise ValueError(f"Version status {version.status} cannot be approved.")

        config = version.configuration

        # Create audit approval record
        approval = ClinicalApproval(
            configuration_version_id=version_id,
            approver_id=approver_id,
            approver_name=approver_name,
            professional_designation=professional_designation,
            professional_registration=professional_registration,
            approval_date=datetime.now(timezone.utc),
            status="APPROVED",
            notes=notes,
        )
        db.add(approval)

        # Retire previously active version
        if config.current_version_id and config.current_version_id != version_id:
            old_version = db.get(ClinicalConfigurationVersion, config.current_version_id)
            if old_version:
                old_version.status = "RETIRED"

        version.status = "APPROVED"
        config.current_version_id = version.id

        db.commit()
        db.refresh(approval)
        db.refresh(config)
        return approval

    def seed_baseline_configurations(
        self, db: Session, facility_id: UUID, created_by_id: UUID
    ) -> int:
        """
        Seeds standard clinical instruments for a facility.
        Default status is PENDING_APPROVAL until the institution's Medical Director approves.
        """
        seeded = 0
        today = date.today()
        one_year_later = date(today.year + 1, today.month, today.day)

        for item in DEFAULT_INSTRUMENTS:
            existing = self.get_configuration_by_key(db, facility_id, item["key"])
            if existing:
                continue

            config = ClinicalConfiguration(
                facility_id=facility_id,
                key=item["key"],
                name=item["name"],
                category=item["category"],
                description=item["description"],
                is_active=True,
            )
            db.add(config)
            db.flush()

            version = ClinicalConfigurationVersion(
                configuration_id=config.id,
                version_number=1,
                source_reference=item["source_reference"],
                schema_definition=item["schema_definition"],
                effective_date=today,
                review_date=one_year_later,
                status="PENDING_APPROVAL",
                created_by=created_by_id,
            )
            db.add(version)
            db.flush()
            config.current_version_id = version.id
            seeded += 1

        db.commit()
        logger.info(f"Seeded {seeded} clinical configurations for facility {facility_id}")
        return seeded


clinical_governance_service = ClinicalGovernanceService()
