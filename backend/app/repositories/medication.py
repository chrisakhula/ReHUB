from sqlalchemy import func, or_, select

from app.core.time import business_today
from app.models.medication import DrugBatch, Medication, MedicationDose, Prescription
from app.repositories.care import CareRepository


class MedicationRepository(CareRepository):
    def prescription(self, prescription_id, lock=False):
        return self.require(Prescription, prescription_id, lock)

    def due(self, paging, admission_id=None, ward_id=None, day=None, round_time=None):
        from datetime import datetime, time, timedelta
        from zoneinfo import ZoneInfo

        from app.models.clients import Admission, Bed, BedAssignment, Client, Room

        stmt = (
            select(MedicationDose, Prescription, Admission, Client)
            .join(Prescription, MedicationDose.prescription_id == Prescription.id)
            .join(Admission, MedicationDose.admission_id == Admission.id)
            .join(Client, Admission.client_id == Client.id)
            .where(
                MedicationDose.facility_id == self.actor.facility_id,
                MedicationDose.status == "DUE",
                Prescription.status == "ACTIVE",
                Admission.status.in_(
                    ["ACTIVE", "ON_LEAVE", "HOSPITALIZED", "AWOL", "DISCHARGE_PENDING"]
                ),
            )
        )
        if paging.get("q"):
            escaped = paging["q"].replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(
                or_(
                    *(
                        field.ilike(f"%{escaped}%", escape="\\")
                        for field in (
                            Client.first_name,
                            Client.surname,
                            Client.client_number,
                            Admission.admission_number,
                            Prescription.generic_name,
                        )
                    )
                )
            )
        if paging.get("start"):
            stmt = stmt.where(MedicationDose.scheduled_at >= paging["start"])
        if paging.get("end"):
            stmt = stmt.where(MedicationDose.scheduled_at <= paging["end"])
        if admission_id:
            self.admission(admission_id, writable=False)
            stmt = stmt.where(MedicationDose.admission_id == admission_id)
        if ward_id:
            stmt = (
                stmt.join(BedAssignment, BedAssignment.admission_id == Admission.id)
                .join(Bed, BedAssignment.bed_id == Bed.id)
                .join(Room, Bed.room_id == Room.id)
                .where(Room.wing_id == ward_id, BedAssignment.ended_at.is_(None))
            )
        if day:
            start = datetime.combine(day, time.min, ZoneInfo("Africa/Nairobi"))
            stmt = stmt.where(
                MedicationDose.scheduled_at >= start,
                MedicationDose.scheduled_at < start + timedelta(days=1),
            )
        if round_time:
            stmt = stmt.where(
                func.to_char(
                    func.timezone("Africa/Nairobi", MedicationDose.scheduled_at), "HH24:MI"
                )
                == round_time
            )
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        ordering = getattr(MedicationDose, paging["sort"], None)
        if paging["sort"] not in {"created_at", "updated_at", "scheduled_at"} or ordering is None:
            from fastapi import HTTPException

            raise HTTPException(422, "Invalid medication round sort")
        rows = self.db.execute(
            stmt.order_by(
                ordering.desc() if paging["direction"] == "desc" else ordering.asc(),
                MedicationDose.id,
            )
            .offset((paging["page"] - 1) * paging["page_size"])
            .limit(paging["page_size"])
        ).all()
        from app.models.medication import MedicationRoute

        route_ids = {d.route_id for d, p, a, c in rows}
        route_names = {
            route.id: route.name
            for route in self.db.scalars(
                select(MedicationRoute).where(MedicationRoute.id.in_(route_ids))
            )
        }
        items = [
            {
                "id": d.id,
                "prescription_id": p.id,
                "admission_id": a.id,
                "admission_number": a.admission_number,
                "client_name": f"{c.first_name} {c.surname}",
                "medication": p.generic_name,
                "strength": p.strength,
                "prescribed_dose": d.prescribed_dose,
                "dose_unit": d.dose_unit,
                "route_id": d.route_id,
                "route_name": route_names.get(d.route_id),
                "scheduled_at": d.scheduled_at,
                "status": d.status,
            }
            for d, p, a, c in rows
        ]
        return {
            "items": items,
            "meta": {"page": paging["page"], "page_size": paging["page_size"], "total": total},
        }

    def alerts(self):
        from datetime import timedelta

        batches = list(
            self.db.scalars(
                select(DrugBatch)
                .where(
                    DrugBatch.facility_id == self.actor.facility_id,
                    DrugBatch.quantity > 0,
                    DrugBatch.expiry_date <= business_today() + timedelta(days=90),
                )
                .order_by(DrugBatch.expiry_date)
                .limit(100)
            )
        )
        quantities = (
            select(DrugBatch.medication_id, func.sum(DrugBatch.quantity).label("quantity"))
            .where(
                DrugBatch.facility_id == self.actor.facility_id,
                DrugBatch.expiry_date >= business_today(),
            )
            .group_by(DrugBatch.medication_id)
            .subquery()
        )
        low_stock = self.db.execute(
            select(Medication, func.coalesce(quantities.c.quantity, 0))
            .outerjoin(quantities, quantities.c.medication_id == Medication.id)
            .where(
                Medication.facility_id == self.actor.facility_id,
                Medication.active.is_(True),
                func.coalesce(quantities.c.quantity, 0) <= Medication.reorder_level,
            )
            .order_by(Medication.generic_name)
            .limit(100)
        ).all()
        return {
            "expiring_batches": batches,
            "low_stock": [
                {
                    "medication_id": m.id,
                    "generic_name": m.generic_name,
                    "quantity": q,
                    "reorder_level": m.reorder_level,
                }
                for m, q in low_stock
            ],
        }
