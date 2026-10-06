"""Discharge and recovery API routes."""

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.discharge import (
    DischargePlan,
    AftercareCase,
    AftercareContact,
    RelapseRecord,
)
from app.schemas.discharge import (
    DischargePlanIn,
    DischargePlanOut,
    AftercareCaseIn,
    AftercareCaseOut,
    AftercareContactIn,
    AftercareContactOut,
    RelapseRecordIn,
    RelapseRecordOut,
)
from app.services.discharge import DischargeService


router = APIRouter(
    prefix="/discharge",
    tags=["Discharge"],
    dependencies=[Depends(require_permission("discharge.view"))]
)

@router.get("/plans")
def get_discharge_plans(
    request: Request,
    page: int = 1,
    admission_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("discharge.view"))
):
    query = db.query(DischargePlan).filter(DischargePlan.facility_id == actor.facility_id)
    if admission_id:
        query = query.filter(DischargePlan.admission_id == admission_id)
    
    total = query.count()
    limit = 20
    items = query.order_by(DischargePlan.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "admission_id": str(i.admission_id),
                "discharge_type": i.discharge_type,
                "status": i.status,
                "discharge_date": i.discharge_date.isoformat() if i.discharge_date else None,
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/plans", response_model=DischargePlanOut)
def create_plan(
    request: Request,
    plan: DischargePlanIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("discharge.edit"))
):
    service = DischargeService(db, request, actor)
    return service.create_discharge_plan(plan)

@router.post("/plans/{plan_id}/status", response_model=DischargePlanOut)
def update_plan_status(
    request: Request,
    plan_id: UUID,
    status: str,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("discharge.edit"))
):
    service = DischargeService(db, request, actor)
    return service.update_discharge_status(plan_id, status)

@router.get("/aftercare")
def get_aftercare_cases(
    request: Request,
    page: int = 1,
    client_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("discharge.view"))
):
    query = db.query(AftercareCase).filter(AftercareCase.facility_id == actor.facility_id)
    if client_id:
        query = query.filter(AftercareCase.client_id == client_id)
    if status:
        query = query.filter(AftercareCase.status == status)
        
    total = query.count()
    limit = 20
    items = query.order_by(AftercareCase.start_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "client_id": str(i.client_id),
                "status": i.status,
                "start_date": i.start_date.isoformat() if i.start_date else None,
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/aftercare", response_model=AftercareCaseOut)
def create_aftercare_case(
    request: Request,
    case: AftercareCaseIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("discharge.edit"))
):
    service = DischargeService(db, request, actor)
    return service.create_aftercare_case(case)

@router.get("/aftercare/{case_id}/contacts")
def get_aftercare_contacts(
    request: Request,
    case_id: UUID,
    page: int = 1,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("discharge.view"))
):
    query = db.query(AftercareContact).filter(
        AftercareContact.facility_id == actor.facility_id,
        AftercareContact.case_id == case_id
    )
        
    total = query.count()
    limit = 20
    items = query.order_by(AftercareContact.contact_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "contact_date": i.contact_date.isoformat() if i.contact_date else None,
                "successful": i.successful,
                "abstinence": i.abstinence,
                "wellbeing": i.wellbeing
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/aftercare/contacts", response_model=AftercareContactOut)
def record_aftercare_contact(
    request: Request,
    contact: AftercareContactIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("discharge.edit"))
):
    service = DischargeService(db, request, actor)
    return service.record_aftercare_contact(contact)

@router.post("/relapse", response_model=RelapseRecordOut)
def record_relapse(
    request: Request,
    relapse: RelapseRecordIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("discharge.edit"))
):
    service = DischargeService(db, request, actor)
    return service.record_relapse(relapse)
