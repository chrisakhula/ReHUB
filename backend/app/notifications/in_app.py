"""In-app notification service for clinical and administrative dashboard feeds."""

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("rehub.notifications.in_app")


class InAppNotificationService:
    """Manages real-time / dashboard alert feeds within ReHUB."""

    def __init__(self):
        self.active_alerts: list[dict[str, Any]] = []

    async def broadcast_crisis_alert(
        self,
        facility_id: UUID,
        alert_id: UUID,
        alert_reference: str,
        severity: str,
        trigger: str,
        target_user_ids: list[UUID] | None = None,
    ) -> bool:
        payload = {
            "facility_id": str(facility_id),
            "alert_id": str(alert_id),
            "alert_reference": alert_reference,
            "severity": severity,
            "trigger": trigger,
            "target_user_ids": [str(u) for u in target_user_ids] if target_user_ids else [],
        }
        self.active_alerts.append(payload)
        logger.info(f"[IN_APP_ALERT] Ref: {alert_reference} for facility {facility_id}")
        return True
