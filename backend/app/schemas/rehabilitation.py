from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.permissions import aware
from app.core.time import EAT

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
AttendanceStatus = Literal["PRESENT", "ABSENT", "EXCUSED", "REFUSED", "LATE"]
SessionType = Literal[
    "INDIVIDUAL_COUNSELLING",
    "GROUP_COUNSELLING",
    "FAMILY_THERAPY",
    "PSYCHOEDUCATION",
    "ADDICTION_COUNSELLING",
    "CBT",
    "RELAPSE_PREVENTION",
    "TRAUMA",
    "MOTIVATIONAL_INTERVIEWING",
    "OCCUPATIONAL_THERAPY",
    "SPIRITUAL_SUPPORT",
    "PEER_SUPPORT",
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="after")
    @classmethod
    def timezone_required(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("Include a timezone")
        return value


class Revision(Input):
    supersedes_id: UUID | None = None
    correction_reason: str = Field("", max_length=500)

    @model_validator(mode="after")
    def reason_required(self):
        if self.supersedes_id and not self.correction_reason:
            raise ValueError("A reason is required when revising a record")
        return self


class SubstanceIn(Input):
    name: str = Field(min_length=2, max_length=100)
    active: bool = True


class SubstanceHistoryIn(Revision):
    admission_id: UUID
    substance_id: UUID
    first_use_age: int | None = Field(None, ge=0, le=120)
    regular_use_age: int | None = Field(None, ge=0, le=120)
    frequency: str = Field(min_length=1, max_length=150)
    quantity: str = Field(min_length=1, max_length=150)
    route: str = Field(min_length=1, max_length=100)
    duration: str = Field("", max_length=150)
    last_use: datetime | None = None
    typical_pattern: str = Field("", max_length=4000)
    maximum_use: str = Field("", max_length=4000)
    withdrawal_symptoms: str = Field("", max_length=4000)
    tolerance: str = Field("", max_length=4000)
    overdose: str = Field("", max_length=4000)
    previous_quit_attempts: str = Field("", max_length=4000)
    longest_abstinence: str = Field("", max_length=150)
    previous_treatment: str = Field("", max_length=4000)
    consequences: str = Field("", max_length=4000)
    status: Literal["CURRENT", "ABSTINENT", "IN_REMISSION", "PAST"] = "CURRENT"

    @model_validator(mode="after")
    def age_order(self):
        if (
            self.first_use_age is not None
            and self.regular_use_age is not None
            and self.regular_use_age < self.first_use_age
        ):
            raise ValueError("Regular use age cannot precede first use age")
        return self


class ResponseOption(Input):
    value: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=200)
    score: int = Field(ge=0, le=100)


class InstrumentQuestion(Input):
    key: str = Field(min_length=1, max_length=70, pattern=r"^[a-zA-Z0-9_]+$")
    text: str = Field(min_length=1, max_length=1000)
    options: list[ResponseOption] = Field(min_length=2, max_length=20)
    domain: str = Field("", max_length=70)
    contributes_to_score: bool = True
    alert_values: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_options(self):
        values = [o.value for o in self.options]
        if len(set(values)) != len(values) or not set(self.alert_values).issubset(values):
            raise ValueError("Option values must be unique and alert values must be valid options")
        return self


class ScoreBand(Input):
    minimum: int = Field(ge=0, le=100000)
    maximum: int = Field(ge=0, le=100000)
    interpretation: str = Field(min_length=1, max_length=500)
    risk_level: RiskLevel
    domain: str = Field("", max_length=70)


class InstrumentIn(Input):
    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z0-9_\-]+$")
    name: str = Field(min_length=2, max_length=150)
    instructions: str = Field("", max_length=4000)
    questions: list[InstrumentQuestion] = Field(min_length=1, max_length=150)
    score_bands: list[ScoreBand] = Field(min_length=1, max_length=100)
    active: bool = True

    @model_validator(mode="after")
    def complete_scoring(self):
        if len({q.key for q in self.questions}) != len(self.questions):
            raise ValueError("Question keys must be unique")
        maxima = {
            "": sum(
                max(o.score for o in q.options) for q in self.questions if q.contributes_to_score
            )
        }
        for q in self.questions:
            if q.domain and q.contributes_to_score:
                maxima[q.domain] = maxima.get(q.domain, 0) + max(o.score for o in q.options)
        if any(b.domain not in maxima for b in self.score_bands):
            raise ValueError("Score band references an unknown domain")
        for domain, maximum in maxima.items():
            bands = sorted(
                (b for b in self.score_bands if b.domain == domain), key=lambda b: b.minimum
            )
            cursor = 0
            for band in bands:
                if band.minimum != cursor or band.maximum < band.minimum:
                    raise ValueError("Score bands must cover scores without gaps or overlaps")
                cursor = band.maximum + 1
            if cursor <= maximum:
                raise ValueError("Score bands must cover the full possible score range")
        return self


class InstrumentAssessmentIn(Input):
    admission_id: UUID
    instrument_id: UUID
    responses: dict[str, str]
    completed_at: datetime
    notes: str = Field("", max_length=4000)


class BiopsychosocialIn(Revision):
    admission_id: UUID
    biological: dict[str, str] = Field(default_factory=dict)
    psychological: dict[str, str] = Field(default_factory=dict)
    social: dict[str, str] = Field(default_factory=dict)
    substance_use: dict[str, str] = Field(default_factory=dict)
    legal: dict[str, str] = Field(default_factory=dict)
    occupational: dict[str, str] = Field(default_factory=dict)
    spiritual: dict[str, str] = Field(default_factory=dict)
    status: Literal["DRAFT", "COMPLETED", "REVIEWED"] = "DRAFT"

    @model_validator(mode="after")
    def bounded_sections(self):
        for section in (
            self.biological,
            self.psychological,
            self.social,
            self.substance_use,
            self.legal,
            self.occupational,
            self.spiritual,
        ):
            if len(section) > 40 or any(len(k) > 100 or len(v) > 6000 for k, v in section.items()):
                raise ValueError("Assessment section exceeds allowed size")
        if self.status != "DRAFT" and any(
            not section or not any(v.strip() for v in section.values())
            for section in (
                self.biological,
                self.psychological,
                self.social,
                self.substance_use,
                self.legal,
                self.occupational,
            )
        ):
            raise ValueError(
                "Complete all six core assessment sections before completion or review"
            )
        return self


class RiskIn(Revision):
    admission_id: UUID
    risk_type: Literal[
        "SUICIDE",
        "SELF_HARM",
        "AGGRESSION",
        "VIOLENCE",
        "ABSCONDING",
        "RELAPSE",
        "OVERDOSE",
        "FALLS",
        "SEIZURE",
        "WITHDRAWAL_COMPLICATION",
        "EXPLOITATION",
        "ABUSE",
        "MEDICAL_DETERIORATION",
    ]
    level: RiskLevel
    risk_factors: str = Field(min_length=3, max_length=6000)
    protective_factors: str = Field("", max_length=6000)
    intervention: str = Field(min_length=3, max_length=6000)
    assigned_staff_id: UUID
    review_date: date
    status: Literal["ACTIVE", "RESOLVED"] = "ACTIVE"


class Objective(Input):
    description: str = Field(min_length=3, max_length=1000)
    measure: str = Field(min_length=3, max_length=1000)
    intervention: str = Field(min_length=3, max_length=2000)
    target_date: date
    outcome: str = Field("", max_length=2000)
    completed: bool = False


class TreatmentPlanIn(Revision):
    admission_id: UUID
    presenting_problem: str = Field(min_length=3, max_length=6000)
    problem_area: str = Field(min_length=3, max_length=300)
    goal: str = Field(min_length=3, max_length=6000)
    objectives: list[Objective] = Field(min_length=1, max_length=50)
    responsible_professional_id: UUID
    start_date: date
    target_date: date
    review_date: date
    outcome: str = Field("", max_length=6000)
    status: Literal["DRAFT", "ACTIVE", "UNDER_REVIEW", "REVISED", "COMPLETED", "CANCELLED"] = (
        "DRAFT"
    )

    @model_validator(mode="after")
    def chronology(self):
        if (
            self.target_date < self.start_date
            or not self.start_date <= self.review_date <= self.target_date
        ):
            raise ValueError("Review date must fall between start and target date")
        if any(not self.start_date <= o.target_date <= self.target_date for o in self.objectives):
            raise ValueError("Objective dates must fall within the treatment period")
        if self.status == "COMPLETED" and (
            not self.outcome or not all(o.completed for o in self.objectives)
        ):
            raise ValueError("Completed plans require an outcome and completed objectives")
        return self


class CaseAssignmentIn(Revision):
    admission_id: UUID
    case_manager_id: UUID
    counsellor_id: UUID
    team_member_ids: list[UUID] = Field(default_factory=list, max_length=30)
    assessment_due: date | None = None
    family_meeting_due: date | None = None
    discharge_preparation_due: date | None = None
    notes: str = Field("", max_length=4000)


class TherapySessionIn(Revision):
    admission_id: UUID
    session_type: SessionType
    therapist_id: UUID
    start_at: datetime
    end_at: datetime
    objective: str = Field(min_length=3, max_length=6000)
    summary: str = Field("", max_length=10000)
    intervention: str = Field("", max_length=6000)
    client_response: str = Field("", max_length=6000)
    progress: str = Field("", max_length=6000)
    homework: str = Field("", max_length=4000)
    risk_concerns: str = Field("", max_length=6000)
    next_session: datetime | None = None
    confidential: bool = False
    status: Literal["SCHEDULED", "COMPLETED", "MISSED", "CANCELLED"] = "COMPLETED"

    @model_validator(mode="after")
    def chronology(self):
        if aware(self.end_at) <= aware(self.start_at):
            raise ValueError("Session end must follow the start")
        if self.next_session and aware(self.next_session) <= aware(self.end_at):
            raise ValueError("Next session must follow this session")
        if self.status == "COMPLETED" and (not self.summary or not self.intervention):
            raise ValueError("Completed sessions require a summary and intervention")
        return self


class GroupSessionIn(Input):
    title: str = Field(min_length=3, max_length=200)
    session_type: SessionType
    topic: str = Field(min_length=3, max_length=300)
    facilitator_id: UUID
    co_facilitator_id: UUID | None = None
    start_at: datetime
    duration_minutes: int = Field(ge=5, le=720)
    location: str = Field(min_length=2, max_length=200)
    objectives: str = Field(min_length=3, max_length=6000)


class GroupAttendanceIn(Revision):
    admission_id: UUID
    status: AttendanceStatus
    private_observation: str = Field("", max_length=6000)


class ProgrammeActivityIn(Input):
    title: str = Field(min_length=3, max_length=200)
    category: str = Field(min_length=2, max_length=100)
    programme: str = Field("", max_length=150)
    start_at: datetime
    duration_minutes: int = Field(ge=5, le=720)
    recurrence: Literal["ONCE", "DAILY", "WEEKLY"] = "ONCE"
    repeat_until: date | None = None
    location: str = Field(min_length=2, max_length=200)
    facilitator_id: UUID

    @model_validator(mode="after")
    def recurrence_period(self):
        if self.recurrence != "ONCE" and (
            not self.repeat_until or self.repeat_until < self.start_at.astimezone(EAT).date()
        ):
            raise ValueError("Recurring activities require an end date on or after the start")
        if (
            self.repeat_until
            and (self.repeat_until - self.start_at.astimezone(EAT).date()).days > 730
        ):
            raise ValueError("Recurring activity periods are limited to two years")
        return self


class ProgrammeAttendanceIn(Revision):
    admission_id: UUID
    occurrence_date: date
    status: AttendanceStatus
    notes: str = Field("", max_length=4000)


class FamilyCommunicationIn(Input):
    admission_id: UUID
    consent_id: UUID
    contact_id: UUID
    communicated_at: datetime
    method: Literal["PHONE", "IN_PERSON", "VIDEO", "LETTER", "EMAIL"]
    purpose: str = Field(min_length=3, max_length=4000)
    shared_information: str = Field(min_length=3, max_length=6000)
    outcome: str = Field("", max_length=4000)
    next_meeting_date: date | None = None
    scope_confirmed: Literal[True]
