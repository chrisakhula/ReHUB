"""Permanent client registry and admission/intake/residential records."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record, utcnow


class FacilityRecord(Record):
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), index=True)


class ReferenceSeed(FacilityRecord, Base):
    __tablename__ = "reference_seeds"
    __table_args__ = (
        UniqueConstraint("facility_id", "domain", "version", name="uq_reference_seed"),
    )
    domain: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer)


class Client(FacilityRecord, Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("facility_id", "client_number"),
        UniqueConstraint("facility_id", "national_id"),
        UniqueConstraint("facility_id", "passport_number"),
    )
    client_number: Mapped[str] = mapped_column(String(40), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    surname: Mapped[str] = mapped_column(String(100), index=True)
    preferred_name: Mapped[str | None] = mapped_column(String(100))
    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(30))
    marital_status: Mapped[str | None] = mapped_column(String(30))
    nationality: Mapped[str] = mapped_column(String(80), default="Kenyan")
    national_id: Mapped[str | None] = mapped_column(String(40), index=True)
    passport_number: Mapped[str | None] = mapped_column(String(40))
    phone: Mapped[str | None] = mapped_column(String(30), index=True)
    email: Mapped[str | None] = mapped_column(String(254))
    county: Mapped[str | None] = mapped_column(String(80))
    sub_county: Mapped[str | None] = mapped_column(String(80))
    ward: Mapped[str | None] = mapped_column(String(80))
    physical_address: Mapped[str | None] = mapped_column(Text)
    occupation: Mapped[str | None] = mapped_column(String(150))
    employer: Mapped[str | None] = mapped_column(String(150))
    religion: Mapped[str | None] = mapped_column(String(100))
    religion_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    religion_policy_required: Mapped[bool] = mapped_column(Boolean, default=False)
    referring_institution: Mapped[str | None] = mapped_column(String(200))
    photo_reference: Mapped[str | None] = mapped_column(String(300))
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    chronic_conditions: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    deceased: Mapped[bool] = mapped_column(Boolean, default=False)


class ClientContact(FacilityRecord, Base):
    __tablename__ = "client_contacts"
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(150))
    relationship: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(254))
    address: Mapped[str | None] = mapped_column(Text)
    authorized_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ClientRevision(FacilityRecord, Base):
    __tablename__ = "client_revisions"
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(500))


class IntakeDocument(FacilityRecord, Base):
    __tablename__ = "intake_documents"
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    referral_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("referrals.id"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str] = mapped_column(String(150))
    mime_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    description: Mapped[str] = mapped_column(String(500), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    confidentiality: Mapped[str] = mapped_column(String(30), default="CONFIDENTIAL")
    size: Mapped[int] = mapped_column(Integer)


class Referral(FacilityRecord, Base):
    __tablename__ = "referrals"
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    referral_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(40))
    referring_person: Mapped[str | None] = mapped_column(String(150))
    organization: Mapped[str | None] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    presenting_problem: Mapped[str] = mapped_column(Text)
    urgency: Mapped[str] = mapped_column(String(20), default="ROUTINE")
    pre_admission_notes: Mapped[str | None] = mapped_column(Text)
    documents: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)
    decision_reason: Mapped[str | None] = mapped_column(Text)


class Screening(FacilityRecord, Base):
    __tablename__ = "pre_admission_screenings"
    referral_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("referrals.id"), index=True)
    current_intoxication: Mapped[bool] = mapped_column(Boolean)
    withdrawal_risk: Mapped[str] = mapped_column(String(20))
    suicide_risk: Mapped[str] = mapped_column(String(20))
    self_harm_risk: Mapped[str] = mapped_column(String(20))
    violence_risk: Mapped[str] = mapped_column(String(20))
    psychosis: Mapped[bool] = mapped_column(Boolean)
    severe_medical_condition: Mapped[bool] = mapped_column(Boolean)
    pregnancy: Mapped[bool] = mapped_column(Boolean)
    seizure_history: Mapped[bool] = mapped_column(Boolean)
    overdose_history: Mapped[bool] = mapped_column(Boolean)
    current_medication: Mapped[str | None] = mapped_column(Text)
    communicable_disease_concerns: Mapped[str | None] = mapped_column(Text)
    accommodation_suitable: Mapped[bool] = mapped_column(Boolean)
    clinically_suitable: Mapped[bool] = mapped_column(Boolean)
    decision: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    screened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Admission(FacilityRecord, Base):
    __tablename__ = "admissions"
    __table_args__ = (
        UniqueConstraint("facility_id", "admission_number"),
        CheckConstraint("expected_duration_days > 0", name="admission_duration_positive"),
        Index(
            "uq_client_open_admission",
            "facility_id",
            "client_id",
            unique=True,
            postgresql_where=text("status NOT IN ('DISCHARGED','TRANSFERRED','DECEASED')"),
            sqlite_where=text("status NOT IN ('DISCHARGED','TRANSFERRED','DECEASED')"),
        ),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    referral_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("referrals.id"), unique=True)
    admission_number: Mapped[str] = mapped_column(String(40), index=True)
    admission_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    admission_type: Mapped[str] = mapped_column(String(30))
    accompanying_person: Mapped[str | None] = mapped_column(String(150))
    referring_organization: Mapped[str | None] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    programme: Mapped[str] = mapped_column(String(150))
    expected_duration_days: Mapped[int] = mapped_column(Integer)
    expected_discharge_date: Mapped[date | None] = mapped_column(Date)
    assigned_counsellor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    assigned_clinician_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    assigned_nurse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    primary_case_manager_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    client_rights_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    treatment_agreement: Mapped[bool] = mapped_column(Boolean, default=False)
    visitor_permissions: Mapped[str | None] = mapped_column(Text)
    communication_permissions: Mapped[str | None] = mapped_column(Text)
    dietary_requirements: Mapped[str | None] = mapped_column(Text)
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    risk_flags: Mapped[list] = mapped_column(JSON, default=list)
    search_permitted: Mapped[bool] = mapped_column(Boolean, default=False)
    search_record: Mapped[str | None] = mapped_column(Text)


class EpisodeOfCare(FacilityRecord, Base):
    __tablename__ = "episodes_of_care"
    admission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admissions.id"), unique=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")


class AdmissionStatusHistory(FacilityRecord, Base):
    __tablename__ = "admission_status_history"
    admission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    previous_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)


class AdmissionIntakeRevision(FacilityRecord, Base):
    __tablename__ = "admission_intake_revisions"
    __table_args__ = (
        UniqueConstraint("admission_id", "version", name="uq_admission_intake_revision"),
    )
    admission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(500))


class Consent(FacilityRecord, Base):
    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint("decision IN ('GRANTED','DECLINED')", name="consent_valid_decision"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    consent_type: Mapped[str] = mapped_column(String(40))
    consent_text: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(30))
    decision: Mapped[str] = mapped_column(String(20))
    consent_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawal_reason: Mapped[str | None] = mapped_column(Text)
    witness: Mapped[str] = mapped_column(String(150))
    notes: Mapped[str | None] = mapped_column(Text)


class PropertyItem(FacilityRecord, Base):
    __tablename__ = "admission_property"
    __table_args__ = (CheckConstraint("quantity > 0", name="property_quantity_positive"),)
    admission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    description: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[int] = mapped_column(Integer)
    storage_location: Mapped[str | None] = mapped_column(String(150))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    returned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    return_reason: Mapped[str | None] = mapped_column(Text)
    client_acknowledgment: Mapped[str] = mapped_column(String(150))


class Wing(FacilityRecord, Base):
    __tablename__ = "wings"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)
    name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Room(FacilityRecord, Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)
    wing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wings.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    sex_restriction: Mapped[str | None] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Bed(FacilityRecord, Base):
    __tablename__ = "beds"
    __table_args__ = (
        UniqueConstraint("room_id", "name"),
        CheckConstraint(
            "status IN ('AVAILABLE','OCCUPIED','RESERVED','CLEANING','MAINTENANCE','UNAVAILABLE')",
            name="bed_valid_status",
        ),
    )
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", index=True)


class BedAssignment(FacilityRecord, Base):
    __tablename__ = "bed_assignments"
    __table_args__ = (
        Index(
            "uq_bed_active_assignment",
            "bed_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
        Index(
            "uq_admission_active_bed",
            "admission_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
    )
    bed_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("beds.id"), index=True)
    admission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text)


class RecordNumber(Base):
    __tablename__ = "record_numbers"
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
