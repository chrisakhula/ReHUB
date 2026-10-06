from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.time import business_today
from app.models.identity import utcnow

Name = Annotated[str, Field(min_length=1, max_length=150)]
Narrative = Annotated[str, Field(min_length=3, max_length=10000)]
RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
ReferralSource = Literal[
    "SELF",
    "FAMILY",
    "HOSPITAL",
    "CLINIC",
    "EMPLOYER",
    "SCHOOL",
    "COURT",
    "PROBATION",
    "POLICE",
    "NACADA",
    "NGO",
    "RELIGIOUS_INSTITUTION",
    "COMMUNITY_ORGANIZATION",
    "OTHER",
]


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ClientIn(Input):
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    middle_name: Annotated[str | None, Field(max_length=100)] = None
    surname: Annotated[str, Field(min_length=1, max_length=100)]
    preferred_name: Annotated[str | None, Field(max_length=100)] = None
    date_of_birth: date
    sex: Literal["MALE", "FEMALE", "INTERSEX", "UNSPECIFIED"]
    marital_status: Annotated[str | None, Field(max_length=30)] = None
    nationality: Annotated[str, Field(min_length=1, max_length=80)] = "Kenyan"
    national_id: Annotated[str | None, Field(min_length=3, max_length=40)] = None
    passport_number: Annotated[str | None, Field(min_length=3, max_length=40)] = None
    phone: Annotated[str | None, Field(min_length=7, max_length=30)] = None
    email: EmailStr | None = None
    county: Annotated[str | None, Field(max_length=80)] = None
    sub_county: Annotated[str | None, Field(max_length=80)] = None
    ward: Annotated[str | None, Field(max_length=80)] = None
    physical_address: Annotated[str | None, Field(max_length=1000)] = None
    occupation: Annotated[str | None, Field(max_length=150)] = None
    employer: Annotated[str | None, Field(max_length=150)] = None
    religion: Annotated[str | None, Field(max_length=100)] = None
    religion_consent: bool = False
    religion_policy_required: bool = False
    referring_institution: Annotated[str | None, Field(max_length=200)] = None
    photo_reference: Annotated[str | None, Field(max_length=300, pattern=r"^[a-zA-Z0-9_-]+$")] = (
        None
    )
    allergies: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list, max_length=100
    )
    chronic_conditions: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list, max_length=100
    )
    active: bool = True
    deceased: bool = False

    @model_validator(mode="after")
    def valid_registry(self):
        if self.date_of_birth > business_today() or self.date_of_birth.year < 1900:
            raise ValueError("Date of birth must be between 1900 and today")
        if self.religion and not (self.religion_consent and self.religion_policy_required):
            raise ValueError("Religion requires institutional policy and explicit consent")
        if self.deceased and self.active:
            raise ValueError("A deceased client must be inactive")
        return self


class ClientUpdate(ClientIn):
    reason: Annotated[str, Field(min_length=3, max_length=500)]


class ContactIn(Input):
    kind: Literal["NEXT_OF_KIN", "EMERGENCY", "PAYER", "AUTHORIZED_FAMILY", "VISITOR", "OTHER"]
    name: Name
    relationship: Annotated[str, Field(min_length=1, max_length=80)]
    phone: Annotated[str, Field(min_length=7, max_length=30)]
    email: EmailStr | None = None
    address: Annotated[str | None, Field(max_length=1000)] = None
    authorized_contact: bool = False
    active: bool = True


class ReferralDocument(Input):
    document_id: UUID
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str | None, Field(max_length=500)] = None


class ReferralIn(Input):
    client_id: UUID
    referral_date: date
    source: ReferralSource
    referring_person: Name | None = None
    organization: Annotated[str | None, Field(max_length=200)] = None
    reason: Narrative
    presenting_problem: Narrative
    urgency: Literal["ROUTINE", "URGENT", "EMERGENCY"] = "ROUTINE"
    pre_admission_notes: Annotated[str | None, Field(max_length=10000)] = None
    documents: list[ReferralDocument] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def valid_date(self):
        if self.referral_date > business_today():
            raise ValueError("Referral date cannot be in the future")
        return self


class ScreeningIn(Input):
    current_intoxication: bool
    withdrawal_risk: RiskLevel
    suicide_risk: RiskLevel
    self_harm_risk: RiskLevel
    violence_risk: RiskLevel
    psychosis: bool
    severe_medical_condition: bool
    pregnancy: bool
    seizure_history: bool
    overdose_history: bool
    current_medication: Annotated[str | None, Field(max_length=10000)] = None
    communicable_disease_concerns: Annotated[str | None, Field(max_length=10000)] = None
    accommodation_suitable: bool
    clinically_suitable: bool
    decision: Literal[
        "SUITABLE",
        "MEDICAL_STABILIZATION",
        "PSYCHIATRIC_EVALUATION",
        "EXTERNAL_REFERRAL",
        "DEFERRED",
        "DECLINED",
    ]
    reason: Narrative

    @model_validator(mode="after")
    def suitability(self):
        if self.decision == "SUITABLE" and (
            not self.accommodation_suitable
            or not self.clinically_suitable
            or self.severe_medical_condition
            or self.psychosis
            or "CRITICAL"
            in [self.withdrawal_risk, self.suicide_risk, self.self_harm_risk, self.violence_risk]
        ):
            raise ValueError(
                (
                    "Critical risks, acute medical/psychotic concerns or unsuitable accommodation "
                    "require evaluation/stabilization before admission"
                )
            )
        return self


class StatusIn(Input):
    status: Annotated[str, Field(min_length=1, max_length=40)]
    reason: Annotated[str, Field(min_length=3, max_length=500)]


class AdmissionIn(Input):
    client_id: UUID
    referral_id: UUID
    admission_date: AwareDatetime
    admission_type: Literal["VOLUNTARY", "COURT_ORDERED", "READMISSION", "TRANSFER"] = "VOLUNTARY"
    accompanying_person: Name | None = None
    referring_organization: Annotated[str | None, Field(max_length=200)] = None
    reason: Narrative
    programme: Name
    expected_duration_days: int = Field(ge=1, le=1095)
    expected_discharge_date: date | None = None
    assigned_counsellor_id: UUID | None = None
    assigned_clinician_id: UUID | None = None
    assigned_nurse_id: UUID | None = None
    primary_case_manager_id: UUID | None = None
    client_rights_acknowledged: bool = False
    treatment_agreement: bool = False
    visitor_permissions: Annotated[str | None, Field(max_length=10000)] = None
    communication_permissions: Annotated[str | None, Field(max_length=10000)] = None
    dietary_requirements: Annotated[str | None, Field(max_length=10000)] = None
    allergies: list[str] = Field(default_factory=list, max_length=100)
    risk_flags: list[str] = Field(default_factory=list, max_length=100)
    search_permitted: bool = False
    search_record: Annotated[str | None, Field(max_length=10000)] = None

    @model_validator(mode="after")
    def dates(self):
        if self.admission_date > utcnow():
            raise ValueError("Admission date cannot be in the future")
        if (
            self.expected_discharge_date
            and self.expected_discharge_date < self.admission_date.date()
        ):
            raise ValueError("Expected discharge must follow admission")
        if self.search_record and not self.search_permitted:
            raise ValueError("Search record requires policy permission")
        return self


class AdmissionAssignmentIn(Input):
    assigned_counsellor_id: UUID | None = None
    assigned_clinician_id: UUID | None = None
    assigned_nurse_id: UUID | None = None
    primary_case_manager_id: UUID | None = None
    reason: Annotated[str, Field(min_length=3, max_length=500)]


class AdmissionIntakeUpdate(Input):
    client_rights_acknowledged: bool
    treatment_agreement: bool
    visitor_permissions: Annotated[str | None, Field(max_length=10000)] = None
    communication_permissions: Annotated[str | None, Field(max_length=10000)] = None
    dietary_requirements: Annotated[str | None, Field(max_length=10000)] = None
    allergies: list[str] = Field(default_factory=list, max_length=100)
    risk_flags: list[str] = Field(default_factory=list, max_length=100)
    search_permitted: bool = False
    search_record: Annotated[str | None, Field(max_length=10000)] = None
    reason: Annotated[str, Field(min_length=3, max_length=500)]

    @model_validator(mode="after")
    def policy_permission(self):
        if self.search_record and not self.search_permitted:
            raise ValueError("Search record requires policy permission")
        return self


class ConsentIn(Input):
    consent_type: Literal[
        "TREATMENT",
        "MEDICATION",
        "INFORMATION_SHARING",
        "FAMILY_COMMUNICATION",
        "PHOTOGRAPHY",
        "MEDIA",
        "RESEARCH",
        "LABORATORY_TESTING",
        "TELEMEDICINE",
        "RELEASE_MEDICAL_INFORMATION",
        "OTHER",
    ]
    consent_text: Narrative
    version: Annotated[str, Field(min_length=1, max_length=30)]
    decision: Literal["GRANTED", "DECLINED"]
    consent_date: AwareDatetime
    expires_at: AwareDatetime | None = None
    witness: Name
    notes: Annotated[str | None, Field(max_length=10000)] = None

    @model_validator(mode="after")
    def dates(self):
        if self.consent_date > utcnow():
            raise ValueError("Consent cannot be future dated")
        if self.expires_at and self.expires_at <= self.consent_date:
            raise ValueError("Expiry must follow consent date")
        return self


class ReasonIn(Input):
    reason: Annotated[str, Field(min_length=3, max_length=500)]


class PropertyIn(Input):
    description: Annotated[str, Field(min_length=1, max_length=300)]
    category: Literal["BELONGINGS", "VALUABLES", "PROHIBITED"]
    quantity: int = Field(ge=1, le=100000)
    storage_location: Annotated[str | None, Field(max_length=150)] = None
    client_acknowledgment: Name


class WingIn(Input):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    active: bool = True


class RoomIn(WingIn):
    wing_id: UUID
    sex_restriction: Literal["MALE", "FEMALE", "INTERSEX", "UNSPECIFIED"] | None = None


class BedIn(Input):
    room_id: UUID
    name: Annotated[str, Field(min_length=1, max_length=80)]


class BedAssignmentIn(Input):
    bed_id: UUID
    reason: Annotated[str, Field(min_length=3, max_length=500)]


def record_out(record):
    """Only mapped columns; never serialize SQLAlchemy internals or relationships."""
    return {column.key: getattr(record, column.key) for column in record.__table__.columns}
