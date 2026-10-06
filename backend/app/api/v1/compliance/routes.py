from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import math
from app.core.database import get_db
from app.models.compliance import Licence, AuditRecord
from app.schemas.compliance import LicenceCreate, LicenceResponse, AuditRecordCreate, AuditRecordResponse

router = APIRouter(prefix="/compliance", tags=["Compliance"])

@router.get("/licences")
def get_licences(page: int = 1, db: Session = Depends(get_db)):
    query = db.query(Licence)
    total = query.count()
    limit = 20
    items = query.order_by(Licence.expiry_date.asc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [LicenceResponse.model_validate(i).model_dump() for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit)}
    }

@router.post("/licences")
def create_licence(item: LicenceCreate, db: Session = Depends(get_db)):
    db_item = Licence(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return LicenceResponse.model_validate(db_item).model_dump()

@router.get("/audits")
def get_audits(page: int = 1, db: Session = Depends(get_db)):
    query = db.query(AuditRecord)
    total = query.count()
    limit = 20
    items = query.order_by(AuditRecord.audit_date.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [AuditRecordResponse.model_validate(i).model_dump() for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit)}
    }

@router.post("/audits")
def create_audit(item: AuditRecordCreate, db: Session = Depends(get_db)):
    db_item = AuditRecord(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return AuditRecordResponse.model_validate(db_item).model_dump()
