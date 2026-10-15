"""Clinical governance, institutional configuration versions, and professional approvals."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.identity import Record


class ClinicalConfiguration(Record, Base):
    """Institutional clinical instruments, assessment thresholds, and risk governance tools."""

    __tablename__ = "clinical_configurations"
    __table_args__ = (
        UniqueConstraint("facility_id", "key", name="uq_clinical_config_facility_key"),
    )

    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    key: Mapped[str] = mapped_column(String(60), index=True)  # AUDIT, ASSIST, DAST, PHQ9, GAD7, CSSRS, etc.
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(60), index=True)  # ASSESSMENT, WITHDRAWAL, RELAPSE, ESCALATION, OBSERVATION
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("clinical_configuration_versions.id"), nullable=True
    )

    versions: Mapped[list["ClinicalConfigurationVersion"]] = relationship(
        back_populates="configuration",
        foreign_keys="ClinicalConfigurationVersion.configuration_id",
        cascade="all, delete-orphan",
    )


class ClinicalConfigurationVersion(Record, Base):
    """Immutable, versioned threshold and rules definition for clinical instruments."""

    __tablename__ = "clinical_configuration_versions"
    __table_args__ = (
        UniqueConstraint(
            "configuration_id", "version_number", name="uq_clinical_config_version_number"
        ),
    )

    configuration_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinical_configurations.id"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    source_reference: Mapped[str] = mapped_column(String(255))  # e.g., "WHO AUDIT-C Guidelines 2020", "C-SSRS Lifetime/Recent"
    schema_definition: Mapped[dict] = mapped_column(JSON)  # thresholds, score bands, cutoffs, rules
    effective_date: Mapped[date] = mapped_column(Date)
    review_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(30), default="DRAFT", index=True
    )  # DRAFT, PENDING_APPROVAL, APPROVED, RETIRED
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    configuration: Mapped["ClinicalConfiguration"] = relationship(
        back_populates="versions", foreign_keys=[configuration_id]
    )
    approvals: Mapped[list["ClinicalApproval"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class ClinicalApproval(Record, Base):
    """Institutional sign-off record by Medical Director or licensed clinical authority."""

    __tablename__ = "clinical_approvals"

    configuration_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinical_configuration_versions.id"), index=True
    )
    approver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    approver_name: Mapped[str] = mapped_column(String(150))
    professional_designation: Mapped[str] = mapped_column(String(150))  # e.g. "Medical Director / Consultant Psychiatrist"
    professional_registration: Mapped[str] = mapped_column(String(100))  # e.g. "KMPDC Reg No. A12345"
    approval_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="APPROVED")  # APPROVED, REJECTED
    notes: Mapped[str] = mapped_column(Text, default="")

    version: Mapped["ClinicalConfigurationVersion"] = relationship(back_populates="approvals")
