"""Shared, facility-scoped access and pagination for care modules."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.identity import User


class CareRepository:
    def __init__(self, db: Session, actor: User):
        self.db = db
        self.actor = actor

    def require(self, model, record_id: UUID, lock: bool = False):
        statement = select(model).where(
            model.id == record_id, model.facility_id == self.actor.facility_id
        )
        if lock:
            statement = statement.with_for_update()
        record = self.db.scalar(statement)
        if record is None:
            raise HTTPException(404, "Record not found")
        return record

    def client(self, record_id: UUID, lock: bool = False):
        from app.models.clients import Client

        return self.require(Client, record_id, lock)

    def admission(self, record_id: UUID, writable: bool = True, lock: bool = False):
        from app.models.clients import Admission

        admission = self.require(Admission, record_id, lock)
        if writable and admission.status not in {
            "ACTIVE",
            "ON_LEAVE",
            "HOSPITALIZED",
            "AWOL",
            "DISCHARGE_PENDING",
        }:
            raise HTTPException(409, "Care records require a current admission")
        return admission

    def staff(self, record_id: UUID | None):
        if record_id is None:
            return None
        user = self.require(User, record_id)
        if not user.active:
            raise HTTPException(422, "Assigned staff account is inactive")
        return user

    def user(self, record_id: UUID | None):
        return self.staff(record_id)

    def page(
        self,
        model,
        page: int,
        page_size: int,
        q: str = "",
        fields=(),
        sort: str = "created_at",
        direction: str = "desc",
        start: datetime | None = None,
        end: datetime | None = None,
        status: str | None = None,
        admission_id: UUID | None = None,
        filters=(),
    ):
        if page < 1 or not 1 <= page_size <= 100:
            raise HTTPException(422, "Page size must be between 1 and 100")
        if start and end and start > end:
            raise HTTPException(422, "Start date must be before end date")
        statement = select(model).where(model.facility_id == self.actor.facility_id, *filters)
        if q and fields:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(
                or_(*(field.ilike(f"%{escaped}%", escape="\\") for field in fields))
            )
        if admission_id:
            self.admission(admission_id, writable=False)
            statement = statement.where(model.admission_id == admission_id)
        if status:
            if not hasattr(model, "status"):
                raise HTTPException(422, "Status filtering is not supported for this record")
            statement = statement.where(model.status == status)
        if start:
            statement = statement.where(model.created_at >= start)
        if end:
            statement = statement.where(model.created_at <= end)
        if sort not in {
            "created_at",
            "updated_at",
            "name",
            "status",
            "scheduled_at",
        } or not hasattr(model, sort):
            raise HTTPException(422, "Unsupported sort field")
        if direction not in {"asc", "desc"}:
            raise HTTPException(422, "Sort direction must be asc or desc")
        total = self.db.scalar(select(func.count()).select_from(statement.subquery()))
        column = getattr(model, sort)
        ordering = column.asc() if direction == "asc" else column.desc()
        rows = list(
            self.db.scalars(
                statement.order_by(ordering, model.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return rows, {"page": page, "page_size": page_size, "total": total}
