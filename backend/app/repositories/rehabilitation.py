from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.permissions import aware
from app.core.security import permission_codes
from app.models.identity import User
from app.models.rehabilitation import AssessmentInstrument, TherapySession
from app.repositories.care import CareRepository


class RehabilitationRepository(CareRepository):
    def require(self, model, record_id, lock=False):
        statement = select(model).where(
            model.id == record_id, model.facility_id == self.actor.facility_id
        )
        if lock:
            statement = statement.with_for_update()
        row = self.db.scalar(statement)
        if not row:
            raise HTTPException(404, "Record not found")
        if (
            model is TherapySession
            and row.confidential
            and "psychotherapy.view" not in permission_codes(self.actor)
        ):
            raise HTTPException(403, "Confidential psychotherapy access is required")
        return row

    def staff(self, record_id, permission=None):
        staff = self.db.scalar(
            select(User).where(
                User.id == record_id,
                User.facility_id == self.actor.facility_id,
                User.active.is_(True),
            )
        )
        if not staff:
            raise HTTPException(422, "Select an active member of staff at your facility")
        if permission and permission not in permission_codes(staff):
            raise HTTPException(422, "Assigned professional lacks the required care permission")
        return staff

    def latest(self, model):
        descendant = select(model.supersedes_id).where(model.supersedes_id.is_not(None))
        return model.id.not_in(descendant)

    def page_records(
        self,
        model,
        page=1,
        page_size=20,
        q="",
        sort="created_at",
        direction="desc",
        start=None,
        end=None,
        status=None,
        admission_id=None,
        current_only=True,
        extra=(),
        root_id=None,
    ):
        if start and end and aware(start) > aware(end):
            raise HTTPException(422, "Start date must precede end date")
        if sort not in {
            "created_at",
            "updated_at",
            "start_at",
            "review_date",
            "completed_at",
            "name",
            "title",
            "version",
        } or not hasattr(model, sort):
            raise HTTPException(422, "Invalid sort field")
        statement = select(model).where(model.facility_id == self.actor.facility_id, *extra)
        if root_id and hasattr(model, "root_id"):
            statement = statement.where(model.root_id == root_id)
        if current_only and model is AssessmentInstrument:
            from sqlalchemy.orm import aliased

            newer = aliased(AssessmentInstrument)
            statement = statement.where(
                ~select(newer.id)
                .where(
                    newer.facility_id == model.facility_id,
                    newer.code == model.code,
                    newer.version > model.version,
                )
                .exists()
            )
        if current_only and hasattr(model, "supersedes_id"):
            statement = statement.where(self.latest(model))
        if model is TherapySession and "psychotherapy.view" not in permission_codes(self.actor):
            statement = statement.where(model.confidential.is_(False))
        if admission_id:
            self.admission(admission_id, writable=False)
            if hasattr(model, "admission_id"):
                statement = statement.where(model.admission_id == admission_id)
        if status and hasattr(model, "status"):
            statement = statement.where(model.status == status)
        if start:
            statement = statement.where(model.created_at >= start)
        if end:
            statement = statement.where(model.created_at <= end)
        # Search identifies records, never confidential note content.
        field = next(
            (
                getattr(model, key)
                for key in ("name", "title", "code", "risk_type", "session_type", "problem_area")
                if hasattr(model, key)
            ),
            None,
        )
        if q and field is not None:
            statement = statement.where(field.ilike(f"%{q}%"))
        total = self.db.scalar(select(func.count()).select_from(statement.subquery()))
        order = getattr(model, sort)
        rows = list(
            self.db.scalars(
                statement.order_by(order.desc() if direction == "desc" else order.asc(), model.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return rows, {"page": page, "page_size": page_size, "total": total}

    def instrument_version(self, code):
        return (
            self.db.scalar(
                select(func.max(AssessmentInstrument.version)).where(
                    AssessmentInstrument.facility_id == self.actor.facility_id,
                    AssessmentInstrument.code == code,
                )
            )
            or 0
        ) + 1
