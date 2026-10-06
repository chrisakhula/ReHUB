import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.care import CareModel, CareOut


class MedicationIn(CareModel):
    generic_name: str = Field(min_length=2, max_length=150)
    brand_name: str | None = Field(default=None, max_length=150)
    formulation: str = Field(min_length=2, max_length=100)
    strength: str = Field(min_length=1, max_length=100)
    dose_unit: str = Field(min_length=1, max_length=30)
    reorder_level: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=3)
    active: bool = True


class MedicationOut(CareOut, MedicationIn):
    pass


class RouteIn(CareModel):
    code: str = Field(min_length=2, max_length=30, pattern=r"^[a-z_]+$")
    name: str = Field(min_length=2, max_length=100)
    active: bool = True


class PrescriptionIn(CareModel):
    admission_id: UUID
    medication_id: UUID
    dose: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    dose_unit: str = Field(min_length=1, max_length=30)
    route_id: UUID
    frequency: str = Field(min_length=2, max_length=100)
    frequency_hours: int | None = Field(default=None, ge=1, le=168)
    scheduled_times: list[str] = Field(default_factory=list, max_length=24)
    start_at: datetime
    stop_at: datetime | None = None
    prn: bool = False
    indication: str = Field(min_length=3, max_length=500)
    instructions: str = Field(default="", max_length=10000)
    allergy_override_reason: str | None = Field(default=None, min_length=3, max_length=500)
    prn_min_interval_hours: int | None = Field(default=None, ge=1, le=168)

    @field_validator("start_at", "stop_at")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("Include a timezone")
        return value

    @field_validator("scheduled_times")
    @classmethod
    def valid_times(cls, value):
        if any(not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time) for time in value):
            raise ValueError("Scheduled times must use HH:MM in East Africa Time")
        if len(value) != len(set(value)):
            raise ValueError("Scheduled times must be unique")
        return sorted(value)

    @model_validator(mode="after")
    def schedule_valid(self):
        if self.stop_at and self.stop_at <= self.start_at:
            raise ValueError("Stop date must be after start date")
        if not self.prn and bool(self.scheduled_times) == bool(self.frequency_hours):
            raise ValueError("Specify either scheduled daily times or a frequency in hours")
        if self.prn and (self.scheduled_times or self.frequency_hours):
            raise ValueError("PRN prescriptions do not generate scheduled doses")
        if not self.prn and self.prn_min_interval_hours:
            raise ValueError("PRN interval is only applicable to PRN prescriptions")
        return self


class PrescriptionChange(PrescriptionIn):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class PrescriptionOut(CareOut, PrescriptionIn):
    client_id: UUID
    generic_name: str
    brand_name: str | None
    formulation: str
    strength: str
    status: str
    prescriber_id: UUID
    version: int


class PrescriptionStatusIn(CareModel):
    status: Literal["ACTIVE", "SUSPENDED", "DISCONTINUED", "COMPLETED"]
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class ScheduleIn(CareModel):
    start: date
    end: date

    @model_validator(mode="after")
    def bound_schedule(self):
        if self.end < self.start or (self.end - self.start).days > 6:
            raise ValueError("Choose a date range of up to seven days")
        return self


class AdministrationIn(CareModel):
    prescription_id: UUID
    dose_id: UUID | None = None
    actual_dose: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    administered_at: datetime
    status: Literal["GIVEN", "REFUSED", "OMITTED", "HELD", "NOT_AVAILABLE", "PATIENT_AWAY", "PRN"]
    reason: str | None = Field(default=None, max_length=500)
    notes: str = Field(default="", max_length=10000)

    @field_validator("administered_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("Include a timezone")
        return value

    @model_validator(mode="after")
    def administration_valid(self):
        if self.status in {"GIVEN", "PRN"} and (self.actual_dose is None or self.actual_dose <= 0):
            raise ValueError("Given medication requires a positive actual dose")
        if self.status not in {"GIVEN", "PRN"} and self.actual_dose not in {None, 0}:
            raise ValueError("Medication not given must not record a positive actual dose")
        if self.status not in {"GIVEN", "PRN"} and (not self.reason or len(self.reason) < 3):
            raise ValueError("Provide a reason when medication is not given")
        return self


class AddendumIn(CareModel):
    correction: str = Field(min_length=3, max_length=10000)
    reason: str = Field(min_length=3, max_length=500)


class SupplierIn(CareModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=254)
    active: bool = True


class BatchIn(CareModel):
    medication_id: UUID
    supplier_id: UUID | None = None
    batch_number: str = Field(min_length=1, max_length=100)
    expiry_date: date
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit: str = Field(min_length=1, max_length=30)
    receipt_reference: str = Field(min_length=2, max_length=100)


class MovementIn(CareModel):
    batch_id: UUID
    movement_type: Literal[
        "DISPENSE",
        "WARD_ISSUE",
        "WARD_RETURN",
        "WARD_USE",
        "RETURN",
        "ADJUST_IN",
        "ADJUST_OUT",
        "DAMAGED",
        "EXPIRED",
    ]
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    prescription_id: UUID | None = None
    location: str | None = Field(default=None, max_length=100)
    reference: str | None = Field(default=None, max_length=100)
    reason: str = Field(min_length=3, max_length=500)


class CountIn(CareModel):
    batch_id: UUID
    counted_quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    reason: str = Field(min_length=3, max_length=500)
