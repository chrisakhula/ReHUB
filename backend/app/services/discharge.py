"""Discharge and recovery operations service layer."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.models.discharge import (
    DischargePlan,
    AftercareCase,
    AftercareContact,
    RelapseRecord,
)
from app.schemas.discharge import (
    DischargePlanIn,
    AftercareCaseIn,
    AftercareContactIn,
    RelapseRecordIn,
)
from app.models.identity import User
from app.models.clients import Admission


class DischargeService:
    def __init__(self, db: Session, request: Request, actor: User):
        self.db = db
        self.request = request
        self.actor = actor

    def event(self, action: str, entity, new: dict = None, previous: dict = None, reason: str = ""):
        audit(self.db, self.request, action, entity.__class__.__name__, self.actor, getattr(entity, "id", None))

    def create_discharge_plan(self, data: DischargePlanIn) -> DischargePlan:
        plan = DischargePlan(
            **data.model_dump(),
            facility_id=self.actor.facility_id,
            responsible_staff_id=data.responsible_staff_id or self.actor.id
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        self.event("discharge.plan_created", plan)
        return plan
        
    def update_discharge_status(self, plan_id: UUID, status: str) -> DischargePlan:
        plan = self.db.query(DischargePlan).filter(DischargePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(404, "Discharge plan not found")
            
        plan.status = status
        
        if status == "DISCHARGED":
            if not plan.discharge_date:
                plan.discharge_date = datetime.utcnow()
                
            # Close the admission
            admission = self.db.query(Admission).filter(Admission.id == plan.admission_id).first()
            if admission:
                admission.status = "DISCHARGED"
                admission.discharge_date = plan.discharge_date
                
        self.db.commit()
        self.db.refresh(plan)
        self.event(f"discharge.plan_status_{status.lower()}", plan)
        return plan

    def create_aftercare_case(self, data: AftercareCaseIn) -> AftercareCase:
        case = AftercareCase(
            **data.model_dump(),
            facility_id=self.actor.facility_id,
            assigned_staff_id=data.assigned_staff_id or self.actor.id
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        self.event("discharge.aftercare_created", case)
        return case

    def record_aftercare_contact(self, data: AftercareContactIn) -> AftercareContact:
        contact = AftercareContact(
            **data.model_dump(),
            facility_id=self.actor.facility_id,
            staff_id=self.actor.id
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        self.event("discharge.aftercare_contact_recorded", contact)
        return contact

    def record_relapse(self, data: RelapseRecordIn) -> RelapseRecord:
        relapse = RelapseRecord(
            **data.model_dump(),
            facility_id=self.actor.facility_id,
            reported_by_id=self.actor.id
        )
        self.db.add(relapse)
        
        # If part of an aftercare case, mark it as relapsed
        if data.case_id:
            case = self.db.query(AftercareCase).filter(AftercareCase.id == data.case_id).first()
            if case:
                case.status = "RELAPSED"
                
        self.db.commit()
        self.db.refresh(relapse)
        self.event("discharge.relapse_recorded", relapse)
        return relapse
