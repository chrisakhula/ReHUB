from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import math
from app.core.database import get_db
from app.models.residential import ResidentMovement, Incident
from app.schemas.residential import ResidentMovementCreate, ResidentMovementResponse, IncidentCreate, IncidentResponse

router = APIRouter(prefix="/residential", tags=["Residential"])

@router.get("/movements")
def get_movements(page: int = 1, admission_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ResidentMovement)
    if admission_id:
        query = query.filter(ResidentMovement.admission_id == admission_id)
    total = query.count()
    limit = 20
    items = query.order_by(ResidentMovement.timestamp.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [ResidentMovementResponse.model_validate(i).model_dump() for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit)}
    }

@router.post("/movements")
def create_movement(movement: ResidentMovementCreate, db: Session = Depends(get_db)):
    db_mov = ResidentMovement(**movement.model_dump())
    db.add(db_mov)
    db.commit()
    db.refresh(db_mov)
    return ResidentMovementResponse.model_validate(db_mov).model_dump()

@router.get("/incidents")
def get_incidents(page: int = 1, db: Session = Depends(get_db)):
    query = db.query(Incident)
    total = query.count()
    limit = 20
    items = query.order_by(Incident.timestamp.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [IncidentResponse.model_validate(i).model_dump() for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit)}
    }

@router.post("/incidents")
def create_incident(incident: IncidentCreate, db: Session = Depends(get_db)):
    db_inc = Incident(**incident.model_dump())
    db.add(db_inc)
    db.commit()
    db.refresh(db_inc)
    return IncidentResponse.model_validate(db_inc).model_dump()
