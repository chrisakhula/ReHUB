"""Residential API routes."""

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.residential import (
    Incident,
    SafeguardingRecord,
    ResidentMovement,
    Visitor,
    VisitorLog,
    Grievance,
    MealPlan,
)
from app.schemas.residential import (
    IncidentIn,
    IncidentOut,
    SafeguardingRecordIn,
    SafeguardingRecordOut,
    ResidentMovementIn,
    ResidentMovementOut,
    VisitorIn,
    VisitorOut,
    VisitorLogIn,
    VisitorLogOut,
    GrievanceIn,
    GrievanceOut,
    MealPlanIn,
    MealPlanOut,
    IncidentAddendumIn,
    IncidentAddendumOut,
)
from app.services.residential import ResidentialService


router = APIRouter(
    prefix="/residential",
    tags=["Residential"],
    dependencies=[Depends(require_permission("residential.view"))]
)

# Movemets
@router.get("/movements")
def get_movements(
    request: Request,
    page: int = 1,
    admission_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.view"))
):
    query = db.query(ResidentMovement).filter(ResidentMovement.facility_id == actor.facility_id)
    if admission_id:
        query = query.filter(ResidentMovement.admission_id == admission_id)
        
    total = query.count()
    limit = 20
    items = query.order_by(ResidentMovement.timestamp.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "admission_id": str(i.admission_id),
                "movement_type": i.movement_type,
                "timestamp": i.timestamp.isoformat() if i.timestamp else None,
                "expected_return": i.expected_return.isoformat() if i.expected_return else None,
                "destination": i.destination
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/movements", response_model=ResidentMovementOut)
def record_movement(
    request: Request,
    movement: ResidentMovementIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.edit"))
):
    service = ResidentialService(db, request, actor)
    return service.record_movement(movement)

# Incidents
@router.get("/incidents")
def get_incidents(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.view"))
):
    query = db.query(Incident).filter(Incident.facility_id == actor.facility_id)
    if status:
        query = query.filter(Incident.status == status)
        
    total = query.count()
    limit = 20
    items = query.order_by(Incident.timestamp.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "category": i.category,
                "severity": i.severity,
                "location": i.location,
                "timestamp": i.timestamp.isoformat() if i.timestamp else None,
                "status": i.status
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/incidents", response_model=IncidentOut)
def report_incident(
    request: Request,
    incident: IncidentIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.edit"))
):
    service = ResidentialService(db, request, actor)
    return service.report_incident(incident)

@router.post("/incidents/addenda", response_model=IncidentAddendumOut)
def add_incident_addendum(
    request: Request,
    addendum: IncidentAddendumIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.edit"))
):
    service = ResidentialService(db, request, actor)
    return service.add_incident_addendum(addendum)

# Safeguarding
@router.get("/safeguarding")
def get_safeguarding_records(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("safeguarding.view")) # Note: Stricter permission
):
    query = db.query(SafeguardingRecord).filter(SafeguardingRecord.facility_id == actor.facility_id)
    if status:
        query = query.filter(SafeguardingRecord.status == status)
        
    total = query.count()
    limit = 20
    items = query.order_by(SafeguardingRecord.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "client_id": str(i.client_id),
                "concern_type": i.concern_type,
                "vulnerable_group": i.vulnerable_group,
                "status": i.status,
                "escalation_level": i.escalation_level
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/safeguarding", response_model=SafeguardingRecordOut)
def create_safeguarding_record(
    request: Request,
    record: SafeguardingRecordIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("safeguarding.edit"))
):
    service = ResidentialService(db, request, actor)
    return service.create_safeguarding_record(record)

# Grievances
@router.get("/grievances")
def get_grievances(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.view"))
):
    query = db.query(Grievance).filter(Grievance.facility_id == actor.facility_id)
    if status:
        query = query.filter(Grievance.status == status)
        
    total = query.count()
    limit = 20
    items = query.order_by(Grievance.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "submitted_by": i.submitted_by,
                "category": i.category,
                "status": i.status,
                "created_at": i.created_at.isoformat() if i.created_at else None
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/grievances", response_model=GrievanceOut)
def file_grievance(
    request: Request,
    grievance: GrievanceIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.edit"))
):
    service = ResidentialService(db, request, actor)
    return service.file_grievance(grievance)

# Visitors
@router.get("/visitors")
def get_visitors(
    request: Request,
    page: int = 1,
    client_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.view"))
):
    query = db.query(Visitor).filter(Visitor.facility_id == actor.facility_id)
    if client_id:
        query = query.filter(Visitor.client_id == client_id)
        
    total = query.count()
    limit = 20
    items = query.order_by(Visitor.name.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "client_id": str(i.client_id),
                "name": i.name,
                "relationship_to_client": i.relationship_to_client,
                "approved": i.approved
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/visitors", response_model=VisitorOut)
def create_visitor(
    request: Request,
    visitor: VisitorIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.edit"))
):
    service = ResidentialService(db, request, actor)
    return service.create_visitor(visitor)

@router.post("/visitors/log", response_model=VisitorLogOut)
def log_visit(
    request: Request,
    log: VisitorLogIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.edit"))
):
    service = ResidentialService(db, request, actor)
    return service.log_visit(log)

# Meal Plans
@router.post("/meal-plans", response_model=MealPlanOut)
def create_meal_plan(
    request: Request,
    plan: MealPlanIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("residential.edit"))
):
    service = ResidentialService(db, request, actor)
    return service.create_meal_plan(plan)
