"""Residential operations service layer."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.models.residential import (
    ResidentMovement,
    Visitor,
    VisitorLog,
    Incident,
    IncidentAddendum,
    SafeguardingRecord,
    Grievance,
    MealPlan,
)
from app.schemas.residential import (
    ResidentMovementIn,
    VisitorIn,
    VisitorLogIn,
    IncidentIn,
    IncidentAddendumIn,
    SafeguardingRecordIn,
    GrievanceIn,
    MealPlanIn,
)


class ResidentialService:
    def __init__(self, db: Session, request: Request, actor):
        self.db = db
        self.request = request
        self.actor = actor

    def event(self, action: str, entity, new: dict = None, previous: dict = None, reason: str = ""):
        audit(self.db, self.request, action, entity.__class__.__name__, self.actor, getattr(entity, "id", None))

    # Resident Movement
    def record_movement(self, data: ResidentMovementIn) -> ResidentMovement:
        movement = ResidentMovement(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        self.event("residential.movement_recorded", movement)
        return movement

    # Visitors
    def create_visitor(self, data: VisitorIn) -> Visitor:
        visitor = Visitor(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(visitor)
        self.db.commit()
        self.db.refresh(visitor)
        self.event("residential.visitor_created", visitor)
        return visitor

    def log_visit(self, data: VisitorLogIn) -> VisitorLog:
        log = VisitorLog(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        self.event("residential.visit_logged", log)
        return log

    # Incidents
    def report_incident(self, data: IncidentIn) -> Incident:
        incident = Incident(
            **data.model_dump(),
            facility_id=self.actor.facility_id,
            reported_by_id=self.actor.id
        )
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        self.event("residential.incident_reported", incident)
        return incident

    def add_incident_addendum(self, data: IncidentAddendumIn) -> IncidentAddendum:
        incident = self.db.query(Incident).filter(Incident.id == data.incident_id).first()
        if not incident:
            raise HTTPException(404, "Incident not found")
            
        addendum = IncidentAddendum(
            **data.model_dump(),
            added_by=self.actor.id
        )
        self.db.add(addendum)
        self.db.commit()
        self.db.refresh(addendum)
        self.event("residential.incident_addendum_added", addendum)
        return addendum

    def update_incident_status(self, incident_id: UUID, status: str, resolution_summary: str = "") -> Incident:
        incident = self.db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise HTTPException(404, "Incident not found")
            
        incident.status = status
        if resolution_summary:
            incident.resolution_summary = resolution_summary
            
        if status == "CLOSED":
            incident.closed_at = datetime.utcnow()
            
        self.db.commit()
        self.db.refresh(incident)
        self.event("residential.incident_status_updated", incident)
        return incident

    # Safeguarding
    def create_safeguarding_record(self, data: SafeguardingRecordIn) -> SafeguardingRecord:
        record = SafeguardingRecord(
            **data.model_dump(),
            facility_id=self.actor.facility_id,
            reported_by_id=self.actor.id
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        self.event("residential.safeguarding_created", record)
        return record

    # Grievances
    def file_grievance(self, data: GrievanceIn) -> Grievance:
        grievance = Grievance(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(grievance)
        self.db.commit()
        self.db.refresh(grievance)
        self.event("residential.grievance_filed", grievance)
        return grievance

    def resolve_grievance(self, grievance_id: UUID, resolution: str, corrective_action: str) -> Grievance:
        grievance = self.db.query(Grievance).filter(Grievance.id == grievance_id).first()
        if not grievance:
            raise HTTPException(404, "Grievance not found")
            
        grievance.status = "RESOLVED"
        grievance.resolution = resolution
        grievance.corrective_action = corrective_action
        grievance.closed_at = datetime.utcnow()
        grievance.investigator_id = self.actor.id
        
        self.db.commit()
        self.db.refresh(grievance)
        self.event("residential.grievance_resolved", grievance)
        return grievance

    # Meal Plans
    def create_meal_plan(self, data: MealPlanIn) -> MealPlan:
        # Deactivate existing meal plans for admission
        self.db.query(MealPlan).filter(
            MealPlan.admission_id == data.admission_id,
            MealPlan.active == True
        ).update({"active": False})
        
        plan = MealPlan(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        self.event("residential.meal_plan_created", plan)
        return plan
