from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.identity import User


class IdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_email(self, email: str, lock: bool = False):
        query = select(User).where(User.email == email.lower())
        return self.db.scalar(query.with_for_update() if lock else query)

    def require(self, model, record_id):
        record = self.db.get(model, record_id)
        if not record:
            raise HTTPException(404, "Record not found")
        return record

    def resolve(self, model, ids):
        unique = set(ids)
        records = list(self.db.scalars(select(model).where(model.id.in_(unique))))
        if len(records) != len(unique):
            raise HTTPException(422, "One or more selected records do not exist")
        return records

    def page(self, model, page, size, query="", fields=(), order=None, filters=()):
        stmt = select(model).where(*filters)
        if query and fields:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(or_(*(f.ilike(f"%{escaped}%", escape="\\") for f in fields)))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = list(
            self.db.scalars(
                stmt.order_by(order if order is not None else model.created_at)
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        return rows, {"page": page, "page_size": size, "total": total}
