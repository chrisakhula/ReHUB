"""Staff service layer."""

from fastapi import Request
from sqlalchemy.orm import Session

from app.audit.events import audit
from app.models.staff import StaffProfile, StaffShift
from app.schemas.staff import StaffProfileIn, StaffShiftIn
from app.models.identity import User


class StaffService:
    def __init__(self, db: Session, request: Request, actor: User):
        self.db = db
        self.request = request
        self.actor = actor

    def event(self, action: str, entity, new: dict = None, previous: dict = None, reason: str = ""):
        audit(self.db, self.request, action, entity.__class__.__name__, self.actor, getattr(entity, "id", None))

    def create_staff_profile(self, data: StaffProfileIn) -> StaffProfile:
        profile = StaffProfile(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        self.event("staff.profile_created", profile)
        return profile

    def schedule_shift(self, data: StaffShiftIn) -> StaffShift:
        shift = StaffShift(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(shift)
        self.db.commit()
        self.db.refresh(shift)
        self.event("staff.shift_scheduled", shift)
        return shift
