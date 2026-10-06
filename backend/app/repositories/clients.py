from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from app.models.clients import Admission, BedAssignment, Client, RecordNumber
from app.models.identity import Facility
from app.repositories.care import CareRepository


class ClientRepository(CareRepository):
    def number(self, kind: str, year: int) -> str:
        # Lock the facility row before creating/reading a counter; serializes first use too.
        self.db.scalar(
            select(Facility).where(Facility.id == self.actor.facility_id).with_for_update()
        )
        counter = self.db.get(RecordNumber, (self.actor.facility_id, kind, year))
        if counter is None:
            counter = RecordNumber(
                facility_id=self.actor.facility_id, kind=kind, year=year, last_value=0
            )
            self.db.add(counter)
        counter.last_value += 1
        self.db.flush()
        return (
            f"ARS-{year}-{counter.last_value:06d}"
            if kind == "CLIENT"
            else f"ADM-{year}-{counter.last_value:06d}"
        )

    def listing(
        self,
        model,
        page=1,
        page_size=20,
        q="",
        status=None,
        sort="created_at",
        direction="desc",
        start: datetime | None = None,
        end: datetime | None = None,
        client_id=None,
        admission_id=None,
        filters=(),
    ):
        if sort not in {
            "created_at",
            "updated_at",
            "client_number",
            "surname",
            "admission_date",
            "admission_number",
            "referral_date",
            "name",
            "status",
            "started_at",
        } or not hasattr(model, sort):
            raise HTTPException(422, "Unsupported sort field")
        if start and end and start > end:
            raise HTTPException(422, "Start must precede end")
        stmt = select(model).where(model.facility_id == self.actor.facility_id, *filters)
        if client_id:
            self.client(client_id)
            stmt = stmt.where(model.client_id == client_id)
        if admission_id:
            self.admission(admission_id, writable=False)
            stmt = stmt.where(model.admission_id == admission_id)
        if status and hasattr(model, "status"):
            stmt = stmt.where(model.status == status)
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            fields = [
                getattr(model, field)
                for field in (
                    "client_number",
                    "first_name",
                    "middle_name",
                    "surname",
                    "national_id",
                    "phone",
                    "admission_number",
                    "name",
                    "source",
                    "organization",
                    "reason",
                    "description",
                )
                if hasattr(model, field)
            ]
            if fields:
                stmt = stmt.where(
                    or_(*(field.ilike(f"%{escaped}%", escape="\\") for field in fields))
                )
        date_column = getattr(
            model, "admission_date", getattr(model, "referral_date", model.created_at)
        )
        if start:
            stmt = stmt.where(date_column >= start)
        if end:
            stmt = stmt.where(date_column <= end)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        column = getattr(model, sort)
        order = column.asc() if direction == "asc" else column.desc()
        return list(
            self.db.scalars(
                stmt.order_by(order, model.id).offset((page - 1) * page_size).limit(page_size)
            )
        ), {"page": page, "page_size": page_size, "total": total}

    def current_assignment(self, admission_id, lock=False):
        stmt = select(BedAssignment).where(
            BedAssignment.admission_id == admission_id,
            BedAssignment.facility_id == self.actor.facility_id,
            BedAssignment.ended_at.is_(None),
        )
        return self.db.scalar(stmt.with_for_update() if lock else stmt)

    def open_admission(self, client_id):
        return self.db.scalar(
            select(Admission).where(
                Admission.client_id == client_id,
                Admission.facility_id == self.actor.facility_id,
                Admission.status.not_in(["DISCHARGED", "TRANSFERRED", "DECEASED"]),
            )
        )

    def identifier_duplicate(self, key, value, record_id=None):
        if not value:
            return None
        stmt = select(Client).where(
            Client.facility_id == self.actor.facility_id, getattr(Client, key) == value
        )
        if record_id:
            stmt = stmt.where(Client.id != record_id)
        return self.db.scalar(stmt)
