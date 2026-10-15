"""Email notification service for institutional alerts."""

import logging
from typing import Any

from app.notifications.base import NotificationProvider
from app.notifications.providers.mock import mock_provider

logger = logging.getLogger("rehub.notifications.email")


class EmailNotificationService:
    """Institutional email notification sender."""

    def __init__(self, provider: NotificationProvider | None = None):
        self.provider = provider or mock_provider

    async def send_crisis_alert_email(
        self,
        recipient_email: str,
        alert_reference: str,
        severity: str,
        trigger: str,
        recipient_name: str = "Clinician",
    ) -> bool:
        subject = f"[CRITICAL ACTION REQUIRED] ReHUB Crisis Alert {alert_reference} ({severity})"
        body = (
            f"Dear {recipient_name},\n\n"
            f"A high-priority clinical crisis alert ({alert_reference}) requires your immediate review.\n"
            f"Trigger Category: {trigger}\n"
            f"Severity: {severity}\n\n"
            f"Please access the ReHUB Clinical Portal to review details and document interventions:\n"
            f"https://rehub.local/clinical\n\n"
            f"Note: Confidential clinical details are restricted to authorized sessions.\n"
            f"ReHUB Clinical Governance System"
        )
        return await self.provider.send(
            recipient=recipient_email,
            subject=subject,
            message=body,
            context={"alert_reference": alert_reference, "channel": "EMAIL"},
        )
