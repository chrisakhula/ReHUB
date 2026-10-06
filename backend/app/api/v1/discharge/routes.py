from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import math
from app.core.database import get_db
from app.models.discharge import DischargePlan, AftercareCase
from app.schemas.discharge import DischargePlanCreate, DischargePlanResponse, AftercareCaseCreate, AftercareCaseResponse

from app.core.permissions import require_permission

router = APIRouter(
    prefix="/discharge",
    tags=["Discharge"],
    dependencies=[Depends(require_permission("admission.view"))]
)
@router.get("/plans")
def get_discharge_plans(page: int = 1, admission_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(DischargePlan)
    if admission_id:
        query = query.filter(DischargePlan.admission_id == admission_id)
    
    total = query.count()
    limit = 20
    items = query.order_by(DischargePlan.discharge_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [DischargePlanResponse.model_validate(i).model_dump() for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit)}
    }

@router.post("/plans")
def create_plan(plan: DischargePlanCreate, db: Session = Depends(get_db)):
    db_plan = DischargePlan(**plan.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return DischargePlanResponse.model_validate(db_plan).model_dump()

@router.get("/aftercare")
def get_aftercare_cases(page: int = 1, db: Session = Depends(get_db)):
    query = db.query(AftercareCase)
    total = query.count()
    limit = 20
    items = query.order_by(AftercareCase.start_date.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [AftercareCaseResponse.model_validate(i).model_dump() for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit)}
    }
