"""System Integration Actor provider for automated, non-human transactions."""

import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import User, Facility, Department, Role

logger = logging.getLogger("rehub.system_actor")

SYSTEM_INTEGRATION_EMAIL = "system.integration@rehub.local"


def get_system_actor(db: Session, facility_id: UUID | None = None) -> User:
    """Retrieve or create the authoritative non-human System Integration User.
    
    This user identity is attributed to automated callbacks (such as M-Pesa Daraja)
    and asynchronous background worker transactions. It cannot be used for interactive login.
    """
    actor = db.scalar(select(User).where(User.email == SYSTEM_INTEGRATION_EMAIL))
    if actor:
        if facility_id and actor.facility_id != facility_id:
            actor.facility_id = facility_id
            db.flush()
        return actor

    # Fallback provisioning if called before seed
    target_facility_id = facility_id
    if not target_facility_id:
        facility = db.scalar(select(Facility).limit(1))
        target_facility_id = facility.id if facility else None

    dept = db.scalar(select(Department).where(Department.name == "Administration"))
    dept_id = dept.id if dept else None

    role = db.scalar(select(Role).where(Role.name == "System Integration"))

    actor = User(
        email=SYSTEM_INTEGRATION_EMAIL,
        full_name="System Integration Actor",
        password_hash="!NON_INTERACTIVE_DISABLED!",
        facility_id=target_facility_id,
        department_id=dept_id,
        roles=[role] if role else [],
        force_password_change=False,
        active=True,
    )
    db.add(actor)
    db.flush()
    logger.info("Provisioned System Integration Actor for facility %s", target_facility_id)
    return actor
