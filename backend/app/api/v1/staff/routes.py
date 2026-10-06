"""Staff API routes."""

import math
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.staff import StaffProfile, StaffShift
from app.schemas.staff import (
    StaffProfileIn, StaffProfileOut,
    StaffShiftIn, StaffShiftOut,
)
from app.services.staff import StaffService


router = APIRouter(
    prefix="/staff",
    tags=["Staff"],
    dependencies=[Depends(require_permission("staff.view"))]
)

@router.get("/profiles")
def get_profiles(page: int = 1, db: Session = Depends(get_db), actor=Depends(require_permission("staff.view"))):
    query = db.query(StaffProfile).filter(StaffProfile.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(StaffProfile.employee_number.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [{"id": str(i.id), "user_id": str(i.user_id), "employee_number": i.employee_number, "designation": i.designation, "department": i.department, "employment_status": i.employment_status} for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/profiles", response_model=StaffProfileOut)
def create_profile(request: Request, profile: StaffProfileIn, db: Session = Depends(get_db), actor=Depends(require_permission("staff.edit"))):
    service = StaffService(db, request, actor)
    return service.create_staff_profile(profile)

@router.get("/shifts")
def get_shifts(page: int = 1, db: Session = Depends(get_db), actor=Depends(require_permission("staff.view"))):
    query = db.query(StaffShift).filter(StaffShift.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(StaffShift.shift_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [{"id": str(i.id), "staff_id": str(i.staff_id), "shift_date": i.shift_date.isoformat() if i.shift_date else None, "shift_type": i.shift_type, "attended": i.attended} for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/shifts", response_model=StaffShiftOut)
def schedule_shift(request: Request, shift: StaffShiftIn, db: Session = Depends(get_db), actor=Depends(require_permission("staff.edit"))):
    service = StaffService(db, request, actor)
    return service.schedule_shift(shift)
