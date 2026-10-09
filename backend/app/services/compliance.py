"""Compliance service layer."""

from fastapi import Request
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.models.compliance import ComplianceRegister, ComplianceInspection
from app.schemas.compliance import ComplianceRegisterIn, ComplianceInspectionIn
from app.models.identity import User


class ComplianceService:
    def __init__(self, db: Session, request: Request, actor: User):
        self.db = db
        self.request = request
        self.actor = actor

    def event(self, action: str, entity, new: dict = None, previous: dict = None, reason: str = ""):
        audit(self.db, self.request, action, entity.__class__.__name__, self.actor, getattr(entity, "id", None))

    def create_register(self, data: ComplianceRegisterIn) -> ComplianceRegister:
        register = ComplianceRegister(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(register)
        self.db.commit()
        self.db.refresh(register)
        self.event("compliance.register_created", register)
        return register

    def record_inspection(self, data: ComplianceInspectionIn) -> ComplianceInspection:
        inspection = ComplianceInspection(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(inspection)
        self.db.commit()
        self.db.refresh(inspection)
        self.event("compliance.inspection_recorded", inspection)
        return inspection
