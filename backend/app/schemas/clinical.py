from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.care import CareModel

TextNote = Annotated[str, Field(max_length=10000)]
RequiredNote = Annotated[str, Field(min_length=2, max_length=10000)]
Priority = Literal["ROUTINE", "URGENT", "EMERGENCY"]
Shift = Literal["DAY", "EVENING", "NIGHT"]


class ClinicalInput(CareModel):
    @field_validator("*", mode="after")
    @classmethod
    def aware_timestamps(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("A timezone is required")
        return value


class AdmissionInput(ClinicalInput):
    admission_id: UUID


class EncounterIn(AdmissionInput):
    encounter_at: datetime
    clinician_id: UUID | None = None
    encounter_type: Literal["ADMISSION", "ROUTINE", "FOLLOW_UP", "EMERGENCY"] = "ROUTINE"
    presenting_complaint: RequiredNote
    medical_history: TextNote = ""
    physical_examination: TextNote = ""
    diagnosis: TextNote = ""
    assessment: TextNote = ""
    plan: TextNote = ""
    follow_up_at: datetime | None = None
    emergency_action: TextNote = ""

    @model_validator(mode="after")
    def emergency_details(self):
        if self.encounter_type == "EMERGENCY" and not self.emergency_action:
            raise ValueError("Document the emergency response")
        if self.follow_up_at and self.follow_up_at < self.encounter_at:
            raise ValueError("Follow-up must be after the encounter")
        return self


class EncounterRevisionIn(EncounterIn):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class ProblemIn(ClinicalInput):
    client_id: UUID
    admission_id: UUID | None = None
    diagnosis: str = Field(min_length=2, max_length=500)
    code: str | None = Field(default=None, max_length=50)
    onset_date: date | None = None


class ProblemUpdate(ClinicalInput):
    status: Literal["ACTIVE", "RESOLVED"]
    reason: str = Field(min_length=3, max_length=500)
    resolution: TextNote = ""


class AllergyIn(ClinicalInput):
    client_id: UUID
    substance: str = Field(min_length=2, max_length=200)
    reaction: str = Field(min_length=2, max_length=500)
    severity: Literal["MILD", "MODERATE", "SEVERE", "UNKNOWN"]


class AllergyUpdate(ClinicalInput):
    status: Literal["ACTIVE", "INACTIVE", "ENTERED_IN_ERROR"]
    reason: str = Field(min_length=3, max_length=500)


class VitalsIn(AdmissionInput):
    observed_at: datetime
    systolic: int | None = Field(default=None, ge=0, le=400)
    diastolic: int | None = Field(default=None, ge=0, le=300)
    pulse: int | None = Field(default=None, ge=0, le=400)
    respiratory_rate: int | None = Field(default=None, ge=0, le=120)
    temperature: float | None = Field(default=None, ge=0, le=60)
    oxygen_saturation: float | None = Field(default=None, ge=0, le=100)
    weight: float | None = Field(default=None, gt=0, le=500)
    height: float | None = Field(default=None, ge=30, le=250)
    blood_glucose: float | None = Field(default=None, ge=0, le=200)
    pain_score: int | None = Field(default=None, ge=0, le=10)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def plausible_vitals(self):
        readings = [
            self.systolic,
            self.diastolic,
            self.pulse,
            self.respiratory_rate,
            self.temperature,
            self.oxygen_saturation,
            self.weight,
            self.height,
            self.blood_glucose,
            self.pain_score,
        ]
        if not any(v is not None for v in readings):
            raise ValueError("Record at least one measurement")
        if (self.systolic is None) != (self.diastolic is None) and not self.notes:
            raise ValueError("Record both systolic and diastolic blood pressure")
        if (
            self.systolic is not None
            and self.diastolic is not None
            and self.systolic <= self.diastolic
        ):
            raise ValueError("Systolic blood pressure must exceed diastolic")
        return self


class OrderIn(AdmissionInput):
    encounter_id: UUID | None = None
    order_type: Literal["MEDICAL", "INVESTIGATION", "REFERRAL", "FOLLOW_UP", "OBSERVATION"]
    description: RequiredNote
    destination: str = Field(default="", max_length=200)
    priority: Priority = "ROUTINE"
    due_at: datetime | None = None


class OrderUpdate(ClinicalInput):
    status: Literal["COMPLETED", "CANCELLED"]
    reason: str = Field(min_length=3, max_length=500)
    completion_note: RequiredNote


class NursingNoteIn(AdmissionInput):
    noted_at: datetime
    shift: Shift
    assessment: RequiredNote
    note: RequiredNote
    interventions: TextNote = ""
    escalation: TextNote = ""
    escalated_to_id: UUID | None = None
    high_risk: bool = False
    observation_due_at: datetime | None = None

    @model_validator(mode="after")
    def escalation_details(self):
        if self.escalated_to_id and not self.escalation:
            raise ValueError("Document the reason for escalation")
        if self.observation_due_at and self.observation_due_at < self.noted_at:
            raise ValueError("Next observation cannot precede the note")
        return self


class NursingRevisionIn(NursingNoteIn):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class ObservationIn(AdmissionInput):
    observed_at: datetime
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    appetite: Literal["GOOD", "FAIR", "POOR", "REFUSED", "NOT_ASSESSED"]
    mood: str = Field(min_length=2, max_length=100)
    hygiene: Literal["INDEPENDENT", "PROMPTED", "ASSISTED", "REFUSED", "NOT_ASSESSED"]
    withdrawal_symptoms: TextNote = ""
    withdrawal_score: int | None = Field(default=None, ge=0, le=1000)
    pain_score: int | None = Field(default=None, ge=0, le=10)
    interventions: TextNote = ""
    escalation: TextNote = ""
    next_observation_at: datetime | None = None

    @model_validator(mode="after")
    def next_observation(self):
        if self.next_observation_at and self.next_observation_at < self.observed_at:
            raise ValueError("Next observation cannot precede this observation")
        return self


class HandoverIn(ClinicalInput):
    admission_id: UUID | None = None
    shift_date: date
    shift: Shift
    summary: RequiredNote
    outstanding_tasks: TextNote = ""
    priority: Priority = "ROUTINE"


class LabRequestIn(AdmissionInput):
    encounter_id: UUID | None = None
    test: str = Field(min_length=2, max_length=200)
    indication: RequiredNote
    provider: str = Field(min_length=2, max_length=200)
    specimen_type: str = Field(min_length=2, max_length=100)
    specimen_at: datetime | None = None
    priority: Priority = "ROUTINE"


class LabResultIn(ClinicalInput):
    resulted_at: datetime
    result: RequiredNote
    units: str = Field(default="", max_length=100)
    reference_range: str = Field(default="", max_length=500)
    abnormal_flag: Literal["NORMAL", "LOW", "HIGH", "CRITICAL", "ABNORMAL", "UNKNOWN"]
    correction_reason: str = Field(default="", max_length=500)


class LabReviewIn(ClinicalInput):
    review_note: RequiredNote


class PdfAttachmentIn(ClinicalInput):
    filename: str = Field(
        min_length=5, max_length=150, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.()-]*\.pdf$"
    )
    content_base64: str = Field(min_length=20, max_length=7_000_000)


class ToxicologySubstance(ClinicalInput):
    substance: str = Field(min_length=2, max_length=100)
    result: Literal["POSITIVE", "NEGATIVE", "INCONCLUSIVE", "NOT_TESTED"]
    concentration: str = Field(default="", max_length=100)


class ToxicologyIn(AdmissionInput):
    test_at: datetime
    reason: RequiredNote
    sample_type: str = Field(min_length=2, max_length=100)
    results: list[ToxicologySubstance] = Field(min_length=1, max_length=30)
    confirmatory_test: str = Field(default="", max_length=500)
    confirmatory_result: str = Field(default="", max_length=500)
    staff_id: UUID | None = None
    acknowledgement: Literal["ACKNOWLEDGED", "DECLINED", "UNABLE", "PENDING"]
    acknowledgement_note: str = Field(default="", max_length=1000)
    follow_up_action: RequiredNote

    @model_validator(mode="after")
    def unique_substances(self):
        names = [r.substance.casefold() for r in self.results]
        if len(names) != len(set(names)):
            raise ValueError("Each substance must appear only once")
        if self.confirmatory_result and not self.confirmatory_test:
            raise ValueError("Specify the confirmatory test")
        return self
