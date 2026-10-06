from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class MedicationRoute(Record, Base):
    __tablename__ = "medication_routes"
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Medication(Record, Base):
    __tablename__ = "medications"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    generic_name: Mapped[str] = mapped_column(String(150))
    brand_name: Mapped[str | None] = mapped_column(String(150))
    formulation: Mapped[str] = mapped_column(String(100))
    strength: Mapped[str] = mapped_column(String(100))
    dose_unit: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    __table_args__ = (
        UniqueConstraint(
            "facility_id", "generic_name", "strength", "formulation", name="uq_medication_catalogue"
        ),
        CheckConstraint("reorder_level >= 0", name="ck_medication_reorder"),
    )


class Prescription(Record, Base):
    __tablename__ = "prescriptions"
    __table_args__ = (
        CheckConstraint("dose > 0", name="ck_prescription_dose"),
        CheckConstraint("stop_at IS NULL OR stop_at > start_at", name="ck_prescription_dates"),
        CheckConstraint(
            "status IN ('DRAFT','ACTIVE','SUSPENDED','DISCONTINUED','COMPLETED')",
            name="ck_prescription_status",
        ),
        CheckConstraint(
            "frequency_hours IS NULL OR frequency_hours > 0", name="ck_prescription_frequency"
        ),
    )
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    medication_id: Mapped[UUID] = mapped_column(ForeignKey("medications.id"), index=True)
    generic_name: Mapped[str] = mapped_column(String(150))
    brand_name: Mapped[str | None] = mapped_column(String(150))
    formulation: Mapped[str] = mapped_column(String(100))
    strength: Mapped[str] = mapped_column(String(100))
    dose: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    dose_unit: Mapped[str] = mapped_column(String(30))
    route_id: Mapped[UUID] = mapped_column(ForeignKey("medication_routes.id"))
    frequency: Mapped[str] = mapped_column(String(100))
    frequency_hours: Mapped[int | None] = mapped_column(Integer)
    scheduled_times: Mapped[list] = mapped_column(JSON, default=list)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stop_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prn: Mapped[bool] = mapped_column(Boolean, default=False)
    indication: Mapped[str] = mapped_column(String(500))
    instructions: Mapped[str] = mapped_column(Text, default="")
    allergy_override_reason: Mapped[str | None] = mapped_column(String(500))
    prn_min_interval_hours: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    prescriber_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)


class PrescriptionRevision(Record, Base):
    __tablename__ = "prescription_revisions"
    __table_args__ = (
        UniqueConstraint("prescription_id", "version", name="uq_prescription_revision"),
    )
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    prescription_id: Mapped[UUID] = mapped_column(ForeignKey("prescriptions.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(500))


class MedicationDose(Record, Base):
    __tablename__ = "medication_doses"
    __table_args__ = (
        UniqueConstraint(
            "prescription_id", "prescription_version", "scheduled_at", name="uq_scheduled_dose"
        ),
    )
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    prescription_id: Mapped[UUID] = mapped_column(ForeignKey("prescriptions.id"), index=True)
    prescription_version: Mapped[int] = mapped_column(Integer)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    prescribed_dose: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    dose_unit: Mapped[str] = mapped_column(String(30))
    route_id: Mapped[UUID] = mapped_column(ForeignKey("medication_routes.id"))
    status: Mapped[str] = mapped_column(String(20), default="DUE", index=True)
    cancelled_reason: Mapped[str | None] = mapped_column(String(500))


class MedicationAdministration(Record, Base):
    __tablename__ = "medication_administrations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('GIVEN','REFUSED','OMITTED','HELD','NOT_AVAILABLE','PATIENT_AWAY','PRN')",
            name="ck_administration_status",
        ),
        CheckConstraint("actual_dose IS NULL OR actual_dose >= 0", name="ck_actual_dose"),
        UniqueConstraint("dose_id", name="uq_dose_administration"),
    )
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id"), index=True)
    prescription_id: Mapped[UUID] = mapped_column(ForeignKey("prescriptions.id"), index=True)
    prescription_version: Mapped[int] = mapped_column(Integer)
    dose_id: Mapped[UUID | None] = mapped_column(ForeignKey("medication_doses.id"), index=True)
    prescribed_dose: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    actual_dose: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    dose_unit: Mapped[str] = mapped_column(String(30))
    route_id: Mapped[UUID] = mapped_column(ForeignKey("medication_routes.id"))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    administered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    administered_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), index=True)
    reason: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str] = mapped_column(Text, default="")


class AdministrationAddendum(Record, Base):
    __tablename__ = "administration_addenda"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    administration_id: Mapped[UUID] = mapped_column(
        ForeignKey("medication_administrations.id"), index=True
    )
    correction: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(500))


class PharmacySupplier(Record, Base):
    __tablename__ = "pharmacy_suppliers"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(254))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DrugBatch(Record, Base):
    __tablename__ = "drug_batches"
    __table_args__ = (
        UniqueConstraint("facility_id", "medication_id", "batch_number", name="uq_drug_batch"),
        CheckConstraint("quantity >= 0", name="ck_batch_quantity"),
    )
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    medication_id: Mapped[UUID] = mapped_column(ForeignKey("medications.id"), index=True)
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("pharmacy_suppliers.id"))
    batch_number: Mapped[str] = mapped_column(String(100))
    expiry_date: Mapped[date] = mapped_column(Date, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    unit: Mapped[str] = mapped_column(String(30))
    receipt_reference: Mapped[str] = mapped_column(String(100))


class WardStock(Record, Base):
    __tablename__ = "ward_stock"
    __table_args__ = (
        UniqueConstraint("batch_id", "location", name="uq_ward_batch"),
        CheckConstraint("quantity >= 0", name="ck_ward_quantity"),
    )
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("drug_batches.id"), index=True)
    location: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)


class PharmacyMovement(Record, Base):
    __tablename__ = "pharmacy_movements"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_movement_quantity"),)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("drug_batches.id"), index=True)
    prescription_id: Mapped[UUID | None] = mapped_column(ForeignKey("prescriptions.id"), index=True)
    movement_type: Mapped[str] = mapped_column(String(30), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    location: Mapped[str | None] = mapped_column(String(100))
    resulting_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    reference: Mapped[str | None] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(500))


class PharmacyStockCount(Record, Base):
    __tablename__ = "pharmacy_stock_counts"
    __table_args__ = (CheckConstraint("counted_quantity >= 0", name="ck_counted_stock"),)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("drug_batches.id"), index=True)
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    counted_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    variance: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    reason: Mapped[str] = mapped_column(String(500))
