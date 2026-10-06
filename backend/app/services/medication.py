from datetime import datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.permissions import aware
from app.core.time import business_today
from app.models.identity import User, utcnow
from app.models.medication import (
    AdministrationAddendum,
    DrugBatch,
    Medication,
    MedicationAdministration,
    MedicationDose,
    MedicationRoute,
    PharmacyMovement,
    PharmacySupplier,
    Prescription,
    PrescriptionRevision,
    WardStock,
)
from app.repositories.medication import MedicationRepository
from app.schemas.medication import PrescriptionOut

PRESCRIPTION_TRANSITIONS = {
    "DRAFT": {"ACTIVE", "DISCONTINUED"},
    "ACTIVE": {"SUSPENDED", "DISCONTINUED", "COMPLETED"},
    "SUSPENDED": {"ACTIVE", "DISCONTINUED", "COMPLETED"},
    "DISCONTINUED": set(),
    "COMPLETED": set(),
}


class MedicationService:
    def __init__(self, db: Session, request: Request, actor: User):
        self.db, self.request, self.actor = db, request, actor
        self.repo = MedicationRepository(db, actor)

    def event(
        self, action: str, entity: str, record_id: UUID, previous=None, new=None, reason=None
    ):
        audit(
            self.db,
            self.request,
            action,
            entity,
            self.actor,
            record_id,
            previous=previous,
            new=new,
            reason=reason,
        )

    def attributed(self, model, data):
        return model(
            **data,
            facility_id=self.actor.facility_id,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )

    def save_medication(self, data, record_id=None):
        record = (
            self.repo.require(Medication, record_id, lock=True)
            if record_id
            else self.attributed(Medication, data.model_dump())
        )
        if record_id:
            previous = {
                key: getattr(record, key)
                for key in ("generic_name", "brand_name", "formulation", "strength", "dose_unit")
            }
            if any(previous[key] != getattr(data, key) for key in previous):
                used = self.db.scalar(
                    select(Prescription.id).where(Prescription.medication_id == record.id).limit(1)
                ) or self.db.scalar(
                    select(DrugBatch.id).where(DrugBatch.medication_id == record.id).limit(1)
                )
                if used:
                    raise HTTPException(
                        409,
                        "Create a new catalogue entry for a changed medicine identity after use",
                    )
            for key, value in data.model_dump().items():
                setattr(record, key, value)
            record.updated_by = self.actor.id
        self.db.add(record)
        self.db.flush()
        self.event(
            "medication.catalogue_updated" if record_id else "medication.catalogue_created",
            "medication",
            record.id,
            new={"active": record.active},
        )
        return record

    def validate_prescription(self, data):
        admission = self.repo.admission(data.admission_id)
        client = self.repo.client(admission.client_id)
        medication = self.repo.require(Medication, data.medication_id)
        route = self.db.get(MedicationRoute, data.route_id)
        if not medication.active or not route or not route.active:
            raise HTTPException(422, "Select an active medication and route")
        if data.dose_unit != medication.dose_unit:
            raise HTTPException(422, "Dose unit must match the medication catalogue")
        allergens = [
            str(value).casefold()
            for value in [*(client.allergies or []), *(admission.allergies or [])]
        ]
        names = [medication.generic_name.casefold(), (medication.brand_name or "").casefold()]
        matches = any(
            a and any(name and (a == name or a in name) for name in names) for a in allergens
        )
        if matches and not data.allergy_override_reason:
            raise HTTPException(
                409,
                (
                    "Medication matches a recorded allergy; prescriber review "
                    "and override reason required"
                ),
            )
        if aware(data.start_at) < aware(admission.admission_date):
            raise HTTPException(422, "Prescription cannot start before admission")
        return admission, medication

    def create_prescription(self, data):
        admission, medication = self.validate_prescription(data)
        record = self.attributed(
            Prescription,
            {
                **data.model_dump(),
                "client_id": admission.client_id,
                "generic_name": medication.generic_name,
                "brand_name": medication.brand_name,
                "formulation": medication.formulation,
                "strength": medication.strength,
                "prescriber_id": self.actor.id,
            },
        )
        self.db.add(record)
        self.db.flush()
        self.snapshot(record, "Initial prescription")
        self.event(
            "prescription.created",
            "prescription",
            record.id,
            new={"version": record.version, "status": record.status},
        )
        return record

    def snapshot(self, record, reason):
        self.db.add(
            self.attributed(
                PrescriptionRevision,
                {
                    "prescription_id": record.id,
                    "version": record.version,
                    "snapshot": PrescriptionOut.model_validate(record).model_dump(mode="json"),
                    "reason": reason,
                },
            )
        )

    def cancel_doses(self, record, reason):
        self.db.execute(
            update(MedicationDose)
            .where(MedicationDose.prescription_id == record.id, MedicationDose.status == "DUE")
            .values(status="CANCELLED", cancelled_reason=reason)
        )

    def change_prescription(self, record_id, data):
        record = self.repo.prescription(record_id, lock=True)
        if record.version != data.expected_version:
            raise HTTPException(409, "Prescription changed; reload before saving")
        if record.status in {"DISCONTINUED", "COMPLETED"}:
            raise HTTPException(409, "Closed prescriptions cannot be edited")
        if data.admission_id != record.admission_id:
            raise HTTPException(422, "Admission cannot be changed on a prescription")
        _, medication = self.validate_prescription(data)
        before = {"version": record.version, "status": record.status}
        self.cancel_doses(record, "Prescription revised")
        for key, value in data.model_dump(exclude={"expected_version", "reason"}).items():
            setattr(record, key, value)
        record.generic_name, record.brand_name = medication.generic_name, medication.brand_name
        record.formulation, record.strength = medication.formulation, medication.strength
        record.prescriber_id, record.updated_by = self.actor.id, self.actor.id
        record.version += 1
        record.status = "DRAFT"
        self.db.flush()
        self.snapshot(record, data.reason)
        self.event(
            "prescription.revised",
            "prescription",
            record.id,
            previous=before,
            new={"version": record.version, "status": record.status},
            reason="Prescriber revision recorded",
        )
        return record

    def prescription_status(self, record_id, data):
        record = self.repo.prescription(record_id, lock=True)
        self.repo.admission(record.admission_id)
        if record.version != data.expected_version:
            raise HTTPException(409, "Prescription changed; reload before saving")
        if data.status not in PRESCRIPTION_TRANSITIONS[record.status]:
            raise HTTPException(409, "Invalid prescription status transition")
        if data.status == "ACTIVE":
            self.validate_prescription(PrescriptionOut.model_validate(record))
            if record.stop_at and aware(record.stop_at) <= utcnow():
                raise HTTPException(409, "An expired prescription cannot be activated")
        previous = {"status": record.status, "version": record.version}
        if data.status != "ACTIVE":
            self.cancel_doses(record, "Prescription status changed")
        record.status, record.updated_by = data.status, self.actor.id
        record.version += 1
        self.db.flush()
        self.snapshot(record, data.reason)
        self.event(
            "prescription.status_changed",
            "prescription",
            record.id,
            previous=previous,
            new={"status": record.status, "version": record.version},
            reason="Status reason stored in prescription revision",
        )
        return record

    def schedule(self, data, admission_id=None):
        stmt = select(Prescription).where(
            Prescription.facility_id == self.actor.facility_id,
            Prescription.status == "ACTIVE",
            Prescription.prn.is_(False),
        )
        if admission_id:
            self.repo.admission(admission_id)
            stmt = stmt.where(Prescription.admission_id == admission_id)
        prescriptions = list(self.db.scalars(stmt.with_for_update()))
        count = 0
        zone = ZoneInfo("Africa/Nairobi")
        range_start = datetime.combine(data.start, time.min, zone)
        range_end = datetime.combine(data.end + timedelta(days=1), time.min, zone)
        for record in prescriptions:
            self.repo.admission(record.admission_id)
            times = []
            if record.scheduled_times:
                current_day = data.start
                while current_day <= data.end:
                    times.extend(
                        datetime.combine(current_day, time.fromisoformat(t), zone)
                        for t in record.scheduled_times
                    )
                    current_day += timedelta(days=1)
            else:
                current = aware(record.start_at)
                interval = timedelta(hours=record.frequency_hours)
                if current < range_start:
                    jumps = (range_start - current) // interval
                    current += jumps * interval
                    if current < range_start:
                        current += interval
                while current < range_end:
                    times.append(current)
                    current += interval
            for scheduled in times:
                if scheduled < aware(record.start_at) or (
                    record.stop_at and scheduled >= aware(record.stop_at)
                ):
                    continue
                existing = self.db.scalar(
                    select(MedicationDose).where(
                        MedicationDose.prescription_id == record.id,
                        MedicationDose.scheduled_at == scheduled,
                        (
                            (MedicationDose.prescription_version == record.version)
                            | (MedicationDose.status == "RECORDED")
                        ),
                    )
                )
                if existing:
                    continue
                self.db.add(
                    self.attributed(
                        MedicationDose,
                        {
                            "admission_id": record.admission_id,
                            "prescription_id": record.id,
                            "prescription_version": record.version,
                            "scheduled_at": scheduled,
                            "prescribed_dose": record.dose,
                            "dose_unit": record.dose_unit,
                            "route_id": record.route_id,
                        },
                    )
                )
                count += 1
        self.db.flush()
        self.event(
            "medication.schedule_generated",
            "admission" if admission_id else "facility",
            admission_id or self.actor.facility_id,
            new={"doses_created": count},
        )
        return {"message": "Medication schedule generated", "doses_created": count}

    def administer(self, data):
        record = self.repo.prescription(data.prescription_id, lock=True)
        self.repo.admission(record.admission_id)
        if record.status != "ACTIVE":
            raise HTTPException(409, "Prescription must be active")
        when = aware(data.administered_at)
        if when > utcnow() + timedelta(minutes=5) or when < aware(record.start_at):
            raise HTTPException(422, "Administration time is outside the valid prescription period")
        if record.stop_at and when >= aware(record.stop_at):
            raise HTTPException(409, "Prescription has expired")
        dose = None
        if record.prn:
            if data.dose_id or data.status not in {"PRN", "REFUSED", "HELD", "NOT_AVAILABLE"}:
                raise HTTPException(
                    422, "PRN medication requires a PRN administration without a scheduled dose"
                )
            if record.prn_min_interval_hours and data.status == "PRN":
                prior = self.db.scalar(
                    select(MedicationAdministration).where(
                        MedicationAdministration.prescription_id == record.id,
                        MedicationAdministration.status == "PRN",
                        MedicationAdministration.administered_at
                        > when - timedelta(hours=record.prn_min_interval_hours),
                        MedicationAdministration.administered_at
                        < when + timedelta(hours=record.prn_min_interval_hours),
                    )
                )
                if prior:
                    raise HTTPException(
                        409, "PRN minimum administration interval would be violated"
                    )
        else:
            if not data.dose_id or data.status == "PRN":
                raise HTTPException(422, "Select a scheduled dose for regular medication")
            dose = self.repo.require(MedicationDose, data.dose_id, lock=True)
            if dose.prescription_id != record.id or dose.status != "DUE":
                raise HTTPException(409, "This dose is unavailable or already recorded")
            if dose.prescription_version != record.version:
                raise HTTPException(409, "Dose belongs to a previous prescription version")
        if data.actual_dose and data.actual_dose != record.dose and not data.reason:
            raise HTTPException(422, "Explain any difference between prescribed and actual dose")
        admin = self.attributed(
            MedicationAdministration,
            {
                **data.model_dump(),
                "client_id": record.client_id,
                "admission_id": record.admission_id,
                "prescription_version": record.version,
                "prescribed_dose": record.dose,
                "dose_unit": record.dose_unit,
                "route_id": record.route_id,
                "scheduled_at": dose.scheduled_at if dose else None,
                "administered_by": self.actor.id,
            },
        )
        self.db.add(admin)
        if dose:
            dose.status, dose.updated_by = "RECORDED", self.actor.id
        self.db.flush()
        self.event(
            "medication.administered",
            "medication_administration",
            admin.id,
            new={
                "status": admin.status,
                "prescription_id": str(record.id),
                "version": record.version,
            },
        )
        return admin

    def addendum(self, record_id, data):
        original = self.repo.require(MedicationAdministration, record_id)
        entry = self.attributed(
            AdministrationAddendum, {**data.model_dump(), "administration_id": original.id}
        )
        self.db.add(entry)
        self.db.flush()
        self.event(
            "medication.administration_addendum",
            "medication_administration",
            original.id,
            new={"addendum_id": str(entry.id)},
        )
        return entry

    def receive_batch(self, data):
        medication = self.repo.require(Medication, data.medication_id)
        if not medication.active or data.expiry_date < business_today():
            raise HTTPException(422, "Cannot receive inactive or expired medication")
        if data.supplier_id:
            supplier = self.repo.require(PharmacySupplier, data.supplier_id)
            if not supplier.active:
                raise HTTPException(422, "Supplier is inactive")
        if data.unit != medication.dose_unit:
            raise HTTPException(422, "Stock unit must match medication dose unit")
        batch = self.attributed(DrugBatch, data.model_dump())
        self.db.add(batch)
        self.db.flush()
        self.db.add(
            self.attributed(
                PharmacyMovement,
                {
                    "batch_id": batch.id,
                    "movement_type": "RECEIPT",
                    "quantity": batch.quantity,
                    "resulting_quantity": batch.quantity,
                    "reference": batch.receipt_reference,
                    "reason": "Goods received",
                },
            )
        )
        self.event(
            "pharmacy.received", "drug_batch", batch.id, new={"quantity": str(batch.quantity)}
        )
        return batch

    def move_stock(self, data):
        batch = self.repo.require(DrugBatch, data.batch_id, lock=True)
        outward = {"DISPENSE", "WARD_ISSUE", "ADJUST_OUT", "DAMAGED", "EXPIRED"}
        ward_types = {"WARD_ISSUE", "WARD_RETURN", "WARD_USE"}
        if (
            data.movement_type in {"DISPENSE", "WARD_ISSUE", "WARD_USE"}
            and batch.expiry_date < business_today()
        ):
            raise HTTPException(409, "Expired stock cannot be dispensed or used")
        if data.movement_type == "EXPIRED" and batch.expiry_date >= business_today():
            raise HTTPException(422, "This batch is not expired")
        if data.movement_type == "DISPENSE":
            if not data.prescription_id:
                raise HTTPException(422, "Dispensing requires a prescription")
            prescription = self.repo.prescription(data.prescription_id, lock=True)
            self.repo.admission(prescription.admission_id)
            if prescription.status != "ACTIVE" or prescription.medication_id != batch.medication_id:
                raise HTTPException(409, "Batch medication must match an active prescription")
            if prescription.stop_at and aware(prescription.stop_at) <= utcnow():
                raise HTTPException(409, "Prescription has expired")
        elif data.prescription_id:
            raise HTTPException(422, "Prescription allocation is only valid for dispensing")
        ward = None
        if data.movement_type in ward_types:
            if not data.location:
                raise HTTPException(422, "Ward location is required")
            ward = self.db.scalar(
                select(WardStock)
                .where(WardStock.batch_id == batch.id, WardStock.location == data.location)
                .with_for_update()
            )
            if not ward:
                if data.movement_type != "WARD_ISSUE":
                    raise HTTPException(409, "No stock exists at this ward location")
                ward = self.attributed(
                    WardStock,
                    {"batch_id": batch.id, "location": data.location, "quantity": Decimal(0)},
                )
                self.db.add(ward)
            if data.movement_type == "WARD_ISSUE":
                ward.quantity += data.quantity
            else:
                if ward.quantity < data.quantity:
                    raise HTTPException(409, "Insufficient ward stock")
                ward.quantity -= data.quantity
            ward.updated_by = self.actor.id
        before = str(batch.quantity)
        if data.movement_type in outward:
            if batch.quantity < data.quantity:
                raise HTTPException(409, "Insufficient pharmacy stock")
            batch.quantity -= data.quantity
        elif data.movement_type != "WARD_USE":
            batch.quantity += data.quantity
        batch.updated_by = self.actor.id
        movement = self.attributed(
            PharmacyMovement, {**data.model_dump(), "resulting_quantity": batch.quantity}
        )
        self.db.add(movement)
        self.db.flush()
        self.event(
            "pharmacy.stock_moved",
            "drug_batch",
            batch.id,
            previous={"quantity": before},
            new={"quantity": str(batch.quantity), "type": data.movement_type},
            reason=data.reason,
        )
        return movement

    def count(self, data):
        from app.models.medication import PharmacyStockCount
        from app.schemas.medication import MovementIn

        batch = self.repo.require(DrugBatch, data.batch_id, lock=True)
        variance = data.counted_quantity - batch.quantity
        count = self.attributed(
            PharmacyStockCount,
            {
                "batch_id": batch.id,
                "expected_quantity": batch.quantity,
                "counted_quantity": data.counted_quantity,
                "variance": variance,
                "reason": data.reason,
            },
        )
        self.db.add(count)
        self.db.flush()
        if variance == 0:
            self.event(
                "pharmacy.stock_count",
                "drug_batch",
                batch.id,
                new={"counted_quantity": str(data.counted_quantity), "variance": "0"},
                reason=data.reason,
            )
            return {"variance": "0", "quantity": str(batch.quantity)}
        movement = self.move_stock(
            MovementIn(
                batch_id=batch.id,
                movement_type="ADJUST_IN" if variance > 0 else "ADJUST_OUT",
                quantity=abs(variance),
                reason=data.reason,
                reference="Stock count",
            )
        )
        return {"variance": str(variance), "quantity": str(movement.resulting_quantity)}
