from fastapi import Request
from sqlalchemy.orm import Session

from app.models.identity import AuditEvent


def audit(
    db: Session,
    request: Request,
    action: str,
    entity: str,
    actor=None,
    entity_id=None,
    previous=None,
    new=None,
    reason=None,
) -> None:
    # Callers supply explicit safe fields: never passwords, tokens or note contents.
    db.add(
        AuditEvent(
            user_id=actor.id if actor else None,
            facility_id=actor.facility_id if actor else None,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id else None,
            previous_values=previous,
            new_values=new,
            reason=reason,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500],
        )
    )
