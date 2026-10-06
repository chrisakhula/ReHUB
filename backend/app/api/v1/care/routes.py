from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.database import get_db
from app.core.permissions import current_user
from app.core.security import permission_codes
from app.models.clients import Admission, Client
from app.models.identity import User

router = APIRouter(prefix="/care", tags=["Care context"])
CARE_READ_PERMISSIONS = {
    "client.view",
    "admission.view",
    "assessment.view",
    "risk.view",
    "therapy.view",
    "clinical.view",
    "nursing.view",
    "medication.view",
    "lab.view",
    "pharmacy.view",
}


@router.get("/options")
def options(
    request: Request,
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_only: bool = True,
    selected_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(current_user),
):
    if not CARE_READ_PERMISSIONS.intersection(permission_codes(actor)):
        raise HTTPException(403, "Care access is required")
    statement = (
        select(Admission, Client)
        .join(Client, Admission.client_id == Client.id)
        .where(Admission.facility_id == actor.facility_id)
    )
    if current_only:
        statement = statement.where(
            Admission.status.not_in(["DISCHARGED", "TRANSFERRED", "DECEASED"])
        )
    if q:
        escaped = q.replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(
            or_(
                *(
                    f.ilike(f"%{escaped}%", escape="\\")
                    for f in (
                        Admission.admission_number,
                        Client.first_name,
                        Client.surname,
                        Client.client_number,
                    )
                )
            )
        )
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    records = db.execute(
        statement.order_by(Admission.admission_date.desc(), Admission.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    selected = None
    if selected_id:
        match = db.execute(
            select(Admission, Client)
            .join(Client, Admission.client_id == Client.id)
            .where(Admission.id == selected_id, Admission.facility_id == actor.facility_id)
        ).first()
        if not match:
            raise HTTPException(404, "Admission not found")
        a, c = match
        selected = {
            "id": a.id,
            "client_id": c.id,
            "admission_number": a.admission_number,
            "client_number": c.client_number,
            "client_name": f"{c.first_name} {c.surname}",
            "status": a.status,
        }
    staff = list(
        db.scalars(
            select(User)
            .where(User.facility_id == actor.facility_id, User.active.is_(True))
            .order_by(User.full_name)
            .limit(100)
        )
    )
    audit(db, request, "care.context_accessed", "admission", actor)
    return {
        "selected": selected,
        "admissions": [
            {
                "id": a.id,
                "client_id": c.id,
                "admission_number": a.admission_number,
                "client_number": c.client_number,
                "client_name": f"{c.first_name} {c.surname}",
                "status": a.status,
            }
            for a, c in records
        ],
        "staff": [
            {"id": u.id, "full_name": u.full_name, "permissions": sorted(permission_codes(u))}
            for u in staff
        ],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }
