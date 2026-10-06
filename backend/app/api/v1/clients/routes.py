from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.clients import (
    Admission,
    AdmissionStatusHistory,
    Bed,
    BedAssignment,
    Client,
    ClientContact,
    Consent,
    PropertyItem,
    Referral,
    Room,
    Screening,
    Wing,
)
from app.models.identity import User
from app.repositories.clients import ClientRepository
from app.schemas.clients import (
    AdmissionAssignmentIn,
    AdmissionIn,
    AdmissionIntakeUpdate,
    BedAssignmentIn,
    BedIn,
    ClientIn,
    ClientUpdate,
    ConsentIn,
    ContactIn,
    PropertyIn,
    ReasonIn,
    ReferralIn,
    RoomIn,
    ScreeningIn,
    StatusIn,
    WingIn,
    record_out,
)
from app.services.clients import ClientService

router = APIRouter(tags=["Clients and intake"])


def paging(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query("", max_length=100),
    status: str | None = Query(None, max_length=40),
    sort: str = "created_at",
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    start: datetime | None = None,
    end: datetime | None = None,
):
    return dict(
        page=page,
        page_size=page_size,
        q=q,
        status=status,
        sort=sort,
        direction=direction,
        start=start,
        end=end,
    )


def listing(model, db, request, actor, args, **filters):
    rows, meta = ClientRepository(db, actor).listing(model, **args, **filters)
    audit(db, request, f"{model.__tablename__}.list_accessed", model.__tablename__, actor)
    return {"items": [record_out(row) for row in rows], "meta": meta}


@router.get("/clients")
def clients(
    request: Request,
    args=Depends(paging),
    active: bool | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.view")),
):
    filters = [Client.active == active] if active is not None else []
    return listing(Client, db, request, actor, args, filters=filters)


@router.post("/clients", status_code=201)
def create_client(
    data: ClientIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.create")),
):
    return record_out(ClientService(db, request, actor).save_client(data))


@router.get("/clients/{record_id}")
def client(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.view")),
):
    row = ClientRepository(db, actor).client(record_id)
    audit(db, request, "client.accessed", "client", actor, row.id)
    return record_out(row)


@router.put("/clients/{record_id}")
def update_client(
    record_id: UUID,
    data: ClientUpdate,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.update")),
):
    return record_out(ClientService(db, request, actor).save_client(data, record_id))


@router.get("/clients/{client_id}/contacts")
def contacts(
    client_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.view")),
):
    return listing(ClientContact, db, request, actor, args, client_id=client_id)


@router.post("/clients/{client_id}/contacts", status_code=201)
def create_contact(
    client_id: UUID,
    data: ContactIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.update")),
):
    return record_out(ClientService(db, request, actor).contact(client_id, data))


@router.put("/clients/{client_id}/contacts/{record_id}")
def update_contact(
    client_id: UUID,
    record_id: UUID,
    data: ContactIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.update")),
):
    return record_out(ClientService(db, request, actor).contact(client_id, data, record_id))


@router.get("/referrals")
def referrals(
    request: Request,
    args=Depends(paging),
    client_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("referral.view")),
):
    return listing(Referral, db, request, actor, args, client_id=client_id)


@router.post("/referrals", status_code=201)
def create_referral(
    data: ReferralIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("referral.create")),
):
    return record_out(ClientService(db, request, actor).referral(data))


@router.get("/referrals/{record_id}")
def referral(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("referral.view")),
):
    row = ClientRepository(db, actor).require(Referral, record_id)
    audit(db, request, "referral.accessed", "referral", actor, row.id)
    return record_out(row)


@router.post("/referrals/{record_id}/status")
def referral_status(
    record_id: UUID,
    data: StatusIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("referral.update")),
):
    return record_out(ClientService(db, request, actor).referral_status(record_id, data))


@router.get("/referrals/{record_id}/screenings")
def screenings(
    record_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("screening.view")),
):
    ClientRepository(db, actor).require(Referral, record_id)
    return listing(
        Screening, db, request, actor, args, filters=[Screening.referral_id == record_id]
    )


@router.post("/referrals/{record_id}/screenings", status_code=201)
def screen(
    record_id: UUID,
    data: ScreeningIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("screening.create")),
):
    return record_out(ClientService(db, request, actor).screen(record_id, data))


@router.get("/admissions")
def admissions(
    request: Request,
    args=Depends(paging),
    client_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.view")),
):
    result = listing(Admission, db, request, actor, args, client_id=client_id)
    client_ids = {row["client_id"] for row in result["items"]}
    registry = {
        row.id: row
        for row in db.scalars(
            select(Client).where(Client.id.in_(client_ids), Client.facility_id == actor.facility_id)
        )
    }
    for row in result["items"]:
        person = registry[row["client_id"]]
        row.update(
            client_name=f"{person.first_name} {person.surname}", client_number=person.client_number
        )
    return result


@router.post("/admissions", status_code=201)
def create_admission(
    data: AdmissionIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.create")),
):
    return record_out(ClientService(db, request, actor).admit(data))


@router.get("/admissions/{record_id}")
def admission(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.view")),
):
    repo = ClientRepository(db, actor)
    row = repo.admission(record_id, writable=False)
    person = repo.client(row.client_id)
    result = record_out(row)
    current = repo.current_assignment(row.id)
    result.update(
        client_name=f"{person.first_name} {person.surname}",
        client_number=person.client_number,
        current_bed=record_out(current) if current else None,
    )
    audit(db, request, "admission.accessed", "admission", actor, row.id)
    return result


@router.post("/admissions/{record_id}/status")
def admission_status(
    record_id: UUID,
    data: StatusIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.update")),
):
    return record_out(ClientService(db, request, actor).admission_status(record_id, data))


@router.put("/admissions/{record_id}/assignments")
def assignments(
    record_id: UUID,
    data: AdmissionAssignmentIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.assign")),
):
    return record_out(ClientService(db, request, actor).assignments(record_id, data))


@router.put("/admissions/{record_id}/intake")
def amend_intake(
    record_id: UUID,
    data: AdmissionIntakeUpdate,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.update")),
):
    return record_out(ClientService(db, request, actor).update_intake(record_id, data))


@router.get("/admissions/{record_id}/intake/history")
def intake_history(
    record_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.view")),
):
    from app.models.clients import AdmissionIntakeRevision

    return listing(AdmissionIntakeRevision, db, request, actor, args, admission_id=record_id)


@router.get("/admissions/{record_id}/history")
def admission_history(
    record_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.view")),
):
    return listing(AdmissionStatusHistory, db, request, actor, args, admission_id=record_id)


@router.get("/admissions/{record_id}/consents")
def consents(
    record_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("consent.view")),
):
    return listing(Consent, db, request, actor, args, admission_id=record_id)


@router.post("/admissions/{record_id}/consents", status_code=201)
def consent(
    record_id: UUID,
    data: ConsentIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("consent.create")),
):
    return record_out(ClientService(db, request, actor).consent(record_id, data))


@router.post("/consents/{record_id}/withdraw")
def withdraw_consent(
    record_id: UUID,
    data: ReasonIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("consent.withdraw")),
):
    return record_out(ClientService(db, request, actor).withdraw_consent(record_id, data))


@router.get("/admissions/{record_id}/property")
def property_items(
    record_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.view")),
):
    return listing(PropertyItem, db, request, actor, args, admission_id=record_id)


@router.post("/admissions/{record_id}/property", status_code=201)
def add_property(
    record_id: UUID,
    data: PropertyIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.property")),
):
    return record_out(ClientService(db, request, actor).property_item(record_id, data))


@router.post("/property/{record_id}/return")
def return_property(
    record_id: UUID,
    data: ReasonIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.property")),
):
    return record_out(ClientService(db, request, actor).return_property(record_id, data))


@router.get("/residential/wings")
def wings(
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.view")),
):
    return listing(Wing, db, request, actor, args)


@router.post("/residential/wings", status_code=201)
def create_wing(
    data: WingIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.manage")),
):
    return record_out(ClientService(db, request, actor).residential(Wing, data))


@router.get("/residential/rooms")
def rooms(
    request: Request,
    args=Depends(paging),
    wing_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.view")),
):
    filters = [Room.wing_id == wing_id] if wing_id else []
    return listing(Room, db, request, actor, args, filters=filters)


@router.post("/residential/rooms", status_code=201)
def create_room(
    data: RoomIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.manage")),
):
    return record_out(ClientService(db, request, actor).residential(Room, data))


@router.get("/residential/beds")
def beds(
    request: Request,
    args=Depends(paging),
    room_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.view")),
):
    filters = [Bed.room_id == room_id] if room_id else []
    result = listing(Bed, db, request, actor, args, filters=filters)
    room_ids = {row["room_id"] for row in result["items"]}
    room_map = {
        row.id: row
        for row in db.scalars(
            select(Room).where(Room.id.in_(room_ids), Room.facility_id == actor.facility_id)
        )
    }
    active = {
        row.bed_id: row.admission_id
        for row in db.scalars(
            select(BedAssignment).where(
                BedAssignment.bed_id.in_([row["id"] for row in result["items"]]),
                BedAssignment.ended_at.is_(None),
                BedAssignment.facility_id == actor.facility_id,
            )
        )
    }
    wing_map = {
        row.id: row.name
        for row in db.scalars(select(Wing).where(Wing.facility_id == actor.facility_id))
    }
    admission_ids = {value for value in active.values()}
    admission_map = {
        row.id: row.admission_number
        for row in db.scalars(
            select(Admission).where(
                Admission.id.in_(admission_ids), Admission.facility_id == actor.facility_id
            )
        )
    }
    for row in result["items"]:
        row.update(
            room_name=room_map[row["room_id"]].name,
            wing_name=wing_map.get(room_map[row["room_id"]].wing_id),
            admission_number=admission_map.get(active.get(row["id"])),
            wing_id=room_map[row["room_id"]].wing_id,
            admission_id=active.get(row["id"]),
        )
    return result


@router.post("/residential/beds", status_code=201)
def create_bed(
    data: BedIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.manage")),
):
    return record_out(ClientService(db, request, actor).residential(Bed, data))


@router.post("/residential/beds/{record_id}/status")
def bed_status(
    record_id: UUID,
    data: StatusIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.manage")),
):
    return record_out(ClientService(db, request, actor).bed_status(record_id, data))


@router.get("/admissions/{record_id}/bed-history")
def bed_history(
    record_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.view")),
):
    return listing(BedAssignment, db, request, actor, args, admission_id=record_id)


@router.post("/admissions/{record_id}/bed", status_code=201)
def assign_bed(
    record_id: UUID,
    data: BedAssignmentIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.assign")),
):
    return record_out(ClientService(db, request, actor).assign_bed(record_id, data))


@router.post("/admissions/{record_id}/bed/release")
def release_bed(
    record_id: UUID,
    data: ReasonIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.assign")),
):
    return record_out(ClientService(db, request, actor).release_bed(record_id, data))


@router.get("/residential/occupancy")
def occupancy(
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("residential.view")),
):
    counts = dict(
        db.execute(
            select(Bed.status, func.count())
            .where(Bed.facility_id == actor.facility_id)
            .group_by(Bed.status)
        ).all()
    )
    total = sum(counts.values())
    audit(db, request, "residential.occupancy_accessed", "bed", actor)
    return {
        "total": total,
        "occupied": counts.get("OCCUPIED", 0),
        "available": counts.get("AVAILABLE", 0),
        "occupancy_percent": round(counts.get("OCCUPIED", 0) * 100 / total, 1) if total else 0,
        "by_status": counts,
    }


@router.get("/intake/staff")
def intake_staff(
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("admission.view")),
):
    result = listing(User, db, request, actor, args, filters=[User.active.is_(True)])
    result["items"] = [
        {key: row[key] for key in ("id", "full_name", "department_id")} for row in result["items"]
    ]
    return result
