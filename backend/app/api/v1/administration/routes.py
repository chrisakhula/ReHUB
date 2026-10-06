from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.database import get_db
from app.core.permissions import current_user, require_permission
from app.core.security import permission_codes
from app.models.identity import AuditEvent, Department, Facility, Permission, Role, User
from app.repositories.identity import IdentityRepository
from app.schemas.identity import (
    DepartmentIn,
    FacilityIn,
    RoleIn,
    RoleOut,
    UserCreate,
    UserUpdate,
    user_out,
)
from app.services.administration import AdministrationService

router = APIRouter(tags=["Administration"])


def page_args(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query("", max_length=100),
):
    return page, page_size, q


@router.get("/users")
def users(
    request: Request,
    paging=Depends(page_args),
    sort: str = Query("full_name", pattern="^(full_name|email|created_at)$"),
    active: bool | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("users.manage")),
):
    filters = [User.facility_id == actor.facility_id]
    if active is not None:
        filters.append(User.active == active)
    rows, meta = IdentityRepository(db).page(
        User,
        *paging,
        fields=(User.full_name, User.email),
        order=getattr(User, sort),
        filters=filters,
    )
    audit(db, request, "user.list_accessed", "user", actor)
    return {"items": [user_out(u) for u in rows], "meta": meta}


@router.post("/users", status_code=201)
def create_user(
    data: UserCreate,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("users.manage")),
):
    return user_out(AdministrationService(db, request, actor).create_user(data))


@router.put("/users/{record_id}")
def update_user(
    record_id: UUID,
    data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("users.manage")),
):
    return user_out(AdministrationService(db, request, actor).update_user(record_id, data))


@router.get("/roles")
def roles(
    paging=Depends(page_args),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(current_user),
):
    from fastapi import HTTPException

    if not {"users.manage", "roles.manage"}.intersection(permission_codes(actor)):
        raise HTTPException(403, "You do not have permission for this action")
    rows, meta = IdentityRepository(db).page(Role, *paging, fields=(Role.name,), order=Role.name)
    return {"items": [RoleOut.model_validate(r) for r in rows], "meta": meta}


@router.post("/roles", status_code=201, response_model=RoleOut)
def create_role(
    data: RoleIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("roles.manage")),
):
    return AdministrationService(db, request, actor).save_role(data)


@router.put("/roles/{record_id}", response_model=RoleOut)
def update_role(
    record_id: UUID,
    data: RoleIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("roles.manage")),
):
    return AdministrationService(db, request, actor).save_role(data, record_id)


@router.get("/permissions")
def permissions(
    paging=Depends(page_args),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(current_user),
):
    from fastapi import HTTPException

    if not {"roles.manage", "users.manage"}.intersection(permission_codes(actor)):
        raise HTTPException(403, "You do not have permission for this action")
    rows, meta = IdentityRepository(db).page(
        Permission, *paging, fields=(Permission.code,), order=Permission.code
    )
    return {"items": rows, "meta": meta}


@router.get("/departments")
def departments(
    paging=Depends(page_args),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(current_user),
):
    rows, meta = IdentityRepository(db).page(
        Department, *paging, fields=(Department.name,), order=Department.name
    )
    return {"items": rows, "meta": meta}


@router.post("/departments", status_code=201)
def create_department(
    data: DepartmentIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("departments.manage")),
):
    return AdministrationService(db, request, actor).save_department(data)


@router.put("/departments/{record_id}")
def update_department(
    record_id: UUID,
    data: DepartmentIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("departments.manage")),
):
    return AdministrationService(db, request, actor).save_department(data, record_id)


@router.get("/settings")
def settings(db: Session = Depends(get_db, scope="function"), actor=Depends(current_user)):
    return IdentityRepository(db).require(Facility, actor.facility_id)


@router.put("/settings")
def save_settings(
    data: FacilityIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("settings.manage")),
):
    facility = IdentityRepository(db).require(Facility, actor.facility_id)
    previous = {key: getattr(facility, key) for key in type(data).model_fields}
    for key, value in data.model_dump().items():
        setattr(facility, key, value)
    facility.updated_by = actor.id
    audit(
        db,
        request,
        "settings.updated",
        "facility",
        actor,
        facility.id,
        previous=previous,
        new=data.model_dump(mode="json"),
    )
    return facility


@router.get("/audit")
def audit_events(
    request: Request,
    paging=Depends(page_args),
    action: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("audit.view")),
):
    from fastapi import HTTPException

    from app.core.permissions import aware

    if start and end and aware(start) > aware(end):
        raise HTTPException(422, "Start date must be before end date")
    filters = [AuditEvent.facility_id == actor.facility_id]
    if action:
        filters.append(AuditEvent.action == action)
    if start:
        filters.append(AuditEvent.timestamp >= start)
    if end:
        filters.append(AuditEvent.timestamp <= end)
    stmt = select(AuditEvent).where(*filters)
    if paging[2]:
        stmt = stmt.where(AuditEvent.action.ilike(f"%{paging[2]}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = list(
        db.scalars(
            stmt.order_by(AuditEvent.timestamp.desc())
            .offset((paging[0] - 1) * paging[1])
            .limit(paging[1])
        )
    )
    audit(db, request, "audit.accessed", "audit", actor)
    return {"items": items, "meta": {"page": paging[0], "page_size": paging[1], "total": total}}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db, scope="function"), actor=Depends(current_user)):
    counts = {}
    for key, model, permission in (
        ("users", User, "users.manage"),
        ("roles", Role, "roles.manage"),
        ("departments", Department, "departments.manage"),
        ("audit_events", AuditEvent, "audit.view"),
    ):
        if permission in permission_codes(actor):
            stmt = select(func.count()).select_from(model)
            if model is User:
                stmt = stmt.where(User.facility_id == actor.facility_id)
            if model is AuditEvent:
                stmt = stmt.where(AuditEvent.facility_id == actor.facility_id)
            counts[key] = db.scalar(stmt)
    return {"counts": counts, "phase": 5, "implemented_phases": [1, 2, 3, 4, 5]}
