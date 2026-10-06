"""Compliance API routes."""

import math
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.compliance import ComplianceRegister, ComplianceInspection
from app.schemas.compliance import (
    ComplianceRegisterIn, ComplianceRegisterOut,
    ComplianceInspectionIn, ComplianceInspectionOut,
)
from app.services.compliance import ComplianceService


router = APIRouter(
    prefix="/compliance",
    tags=["Compliance"],
    dependencies=[Depends(require_permission("compliance.view"))]
)

@router.get("/registers")
def get_registers(page: int = 1, db: Session = Depends(get_db), actor=Depends(require_permission("compliance.view"))):
    query = db.query(ComplianceRegister).filter(ComplianceRegister.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(ComplianceRegister.expiry_date.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [{"id": str(i.id), "category": i.category, "authority": i.authority, "reference_number": i.reference_number, "expiry_date": i.expiry_date.isoformat() if i.expiry_date else None, "status": i.status} for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/registers", response_model=ComplianceRegisterOut)
def create_register(request: Request, register: ComplianceRegisterIn, db: Session = Depends(get_db), actor=Depends(require_permission("compliance.edit"))):
    service = ComplianceService(db, request, actor)
    return service.create_register(register)

@router.get("/inspections")
def get_inspections(page: int = 1, db: Session = Depends(get_db), actor=Depends(require_permission("compliance.view"))):
    query = db.query(ComplianceInspection).filter(ComplianceInspection.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(ComplianceInspection.inspection_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [{"id": str(i.id), "title": i.title, "inspection_date": i.inspection_date.isoformat() if i.inspection_date else None, "inspector_name": i.inspector_name, "passed": i.passed, "status": i.status} for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/inspections", response_model=ComplianceInspectionOut)
def record_inspection(request: Request, inspection: ComplianceInspectionIn, db: Session = Depends(get_db), actor=Depends(require_permission("compliance.edit"))):
    service = ComplianceService(db, request, actor)
    return service.record_inspection(inspection)
