from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.medication import (
    AdministrationAddendum,
    DrugBatch,
    Medication,
    MedicationAdministration,
    MedicationRoute,
    PharmacyMovement,
    PharmacySupplier,
    Prescription,
    PrescriptionRevision,
    WardStock,
)
from app.repositories.medication import MedicationRepository
from app.schemas.care import care_paging
from app.schemas.medication import (
    AddendumIn,
    AdministrationIn,
    BatchIn,
    CountIn,
    MedicationIn,
    MedicationOut,
    MovementIn,
    PrescriptionChange,
    PrescriptionIn,
    PrescriptionOut,
    PrescriptionStatusIn,
    RouteIn,
    ScheduleIn,
    SupplierIn,
)
from app.services.medication import MedicationService

router = APIRouter(tags=["Medication and pharmacy"])


def output(row):
    return {column.key: getattr(row, column.key) for column in row.__table__.columns}


def listing(model, db, request, actor, paging, **filters):
    rows, meta = MedicationRepository(db, actor).page(model, **paging, **filters)
    audit(db, request, "medication.records_accessed", model.__tablename__, actor)
    return {"items": [output(row) for row in rows], "meta": meta}


@router.get("/medication/catalogue")
def catalogue(
    request: Request,
    paging=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.view")),
):
    return listing(
        Medication,
        db,
        request,
        actor,
        paging,
        fields=(Medication.generic_name, Medication.brand_name),
    )


@router.post("/medication/catalogue", status_code=201, response_model=MedicationOut)
def create_medication(
    data: MedicationIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.manage")),
):
    return MedicationService(db, request, actor).save_medication(data)


@router.put("/medication/catalogue/{record_id}", response_model=MedicationOut)
def update_medication(
    record_id: UUID,
    data: MedicationIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.manage")),
):
    return MedicationService(db, request, actor).save_medication(data, record_id)


@router.get("/medication/routes")
def routes(
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.view")),
):
    return {
        "items": [
            output(row)
            for row in db.scalars(select(MedicationRoute).order_by(MedicationRoute.name))
        ]
    }


@router.post("/medication/routes", status_code=201)
def create_route(
    data: RouteIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.manage")),
):
    record = MedicationRoute(**data.model_dump(), created_by=actor.id)
    db.add(record)
    db.flush()
    audit(db, request, "medication.route_created", "medication_route", actor, record.id)
    return output(record)


@router.get("/medication/prescriptions")
def prescriptions(
    request: Request,
    paging=Depends(care_paging),
    admission_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.view")),
):
    return listing(
        Prescription,
        db,
        request,
        actor,
        paging,
        admission_id=admission_id,
        status=status,
        fields=(Prescription.generic_name,),
    )


@router.post("/medication/prescriptions", status_code=201, response_model=PrescriptionOut)
def prescribe(
    data: PrescriptionIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.prescribe")),
):
    return MedicationService(db, request, actor).create_prescription(data)


@router.put("/medication/prescriptions/{record_id}", response_model=PrescriptionOut)
def revise_prescription(
    record_id: UUID,
    data: PrescriptionChange,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.prescribe")),
):
    return MedicationService(db, request, actor).change_prescription(record_id, data)


@router.post("/medication/prescriptions/{record_id}/status", response_model=PrescriptionOut)
def prescription_status(
    record_id: UUID,
    data: PrescriptionStatusIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.prescribe")),
):
    return MedicationService(db, request, actor).prescription_status(record_id, data)


@router.get("/medication/prescriptions/{record_id}/history")
def prescription_history(
    record_id: UUID,
    request: Request,
    paging=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.view")),
):
    repo = MedicationRepository(db, actor)
    repo.prescription(record_id)
    return listing(
        PrescriptionRevision,
        db,
        request,
        actor,
        paging,
        filters=(PrescriptionRevision.prescription_id == record_id,),
    )


@router.post("/medication/schedule")
def generate_schedule(
    data: ScheduleIn,
    request: Request,
    admission_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.administer")),
):
    return MedicationService(db, request, actor).schedule(data, admission_id)


@router.get("/medication/due")
def medication_due(
    request: Request,
    paging=Depends(care_paging),
    admission_id: UUID | None = None,
    ward_id: UUID | None = None,
    day: date | None = None,
    round_time: str | None = Query(None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$"),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.view")),
):
    audit(db, request, "medication.due_accessed", "medication_dose", actor)
    return MedicationRepository(db, actor).due(paging, admission_id, ward_id, day, round_time)


@router.get("/medication/administrations")
def administrations(
    request: Request,
    paging=Depends(care_paging),
    admission_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.view")),
):
    return listing(
        MedicationAdministration,
        db,
        request,
        actor,
        paging,
        admission_id=admission_id,
        status=status,
    )


@router.post("/medication/administrations", status_code=201)
def administer(
    data: AdministrationIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.administer")),
):
    return output(MedicationService(db, request, actor).administer(data))


@router.post("/medication/administrations/{record_id}/addenda", status_code=201)
def administration_addendum(
    record_id: UUID,
    data: AddendumIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.administer")),
):
    return output(MedicationService(db, request, actor).addendum(record_id, data))


@router.get("/medication/administrations/{record_id}/addenda")
def administration_addenda(
    record_id: UUID,
    request: Request,
    paging=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("medication.view")),
):
    MedicationRepository(db, actor).require(MedicationAdministration, record_id)
    return listing(
        AdministrationAddendum,
        db,
        request,
        actor,
        paging,
        filters=(AdministrationAddendum.administration_id == record_id,),
    )


@router.get("/pharmacy/suppliers")
def suppliers(
    request: Request,
    paging=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.view")),
):
    return listing(PharmacySupplier, db, request, actor, paging, fields=(PharmacySupplier.name,))


@router.post("/pharmacy/suppliers", status_code=201)
def supplier(
    data: SupplierIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.manage")),
):
    record = MedicationService(db, request, actor).attributed(PharmacySupplier, data.model_dump())
    db.add(record)
    db.flush()
    audit(db, request, "pharmacy.supplier_created", "pharmacy_supplier", actor, record.id)
    return output(record)


@router.get("/pharmacy/batches")
def batches(
    request: Request,
    paging=Depends(care_paging),
    medication_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.view")),
):
    filters = (DrugBatch.medication_id == medication_id,) if medication_id else ()
    return listing(
        DrugBatch, db, request, actor, paging, fields=(DrugBatch.batch_number,), filters=filters
    )


@router.post("/pharmacy/batches", status_code=201)
def receive_batch(
    data: BatchIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.manage")),
):
    return output(MedicationService(db, request, actor).receive_batch(data))


@router.get("/pharmacy/movements")
def movements(
    request: Request,
    paging=Depends(care_paging),
    batch_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.view")),
):
    return listing(
        PharmacyMovement,
        db,
        request,
        actor,
        paging,
        filters=(PharmacyMovement.batch_id == batch_id,) if batch_id else (),
    )


@router.post("/pharmacy/movements", status_code=201)
def move_stock(
    data: MovementIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.dispense")),
):
    if data.movement_type not in {"DISPENSE", "WARD_USE", "WARD_ISSUE", "WARD_RETURN"}:
        from fastapi import HTTPException

        from app.core.security import permission_codes

        if "pharmacy.manage" not in permission_codes(actor):
            raise HTTPException(403, "Stock adjustments require pharmacy management permission")
    return output(MedicationService(db, request, actor).move_stock(data))


@router.post("/pharmacy/counts")
def count_stock(
    data: CountIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.manage")),
):
    return MedicationService(db, request, actor).count(data)


@router.get("/pharmacy/counts")
def count_history(
    request: Request,
    paging=Depends(care_paging),
    batch_id: UUID | None = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.view")),
):
    from app.models.medication import PharmacyStockCount

    return listing(
        PharmacyStockCount,
        db,
        request,
        actor,
        paging,
        filters=(PharmacyStockCount.batch_id == batch_id,) if batch_id else (),
    )


@router.get("/pharmacy/ward-stock")
def ward_stock(
    request: Request,
    paging=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.view")),
):
    return listing(WardStock, db, request, actor, paging, fields=(WardStock.location,))


@router.get("/pharmacy/alerts")
def stock_alerts(
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("pharmacy.view")),
):
    audit(db, request, "pharmacy.alerts_accessed", "pharmacy", actor)
    return MedicationRepository(db, actor).alerts()
