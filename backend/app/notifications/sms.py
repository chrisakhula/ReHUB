"""SMS Notification Service enforcing strict clinical privacy rules."""

import logging
import re
from typing import Any

from app.core.config import get_settings
from app.notifications.base import NotificationProvider
from app.notifications.providers.africastalking import AfricasTalkingProvider
from app.notifications.providers.mock import mock_provider

logger = logging.getLogger("rehub.notifications.sms")
settings = get_settings()

# Prohibited clinical terms in external SMS broadcasts (institutional safeguard)
PROHIBITED_SMS_PATTERNS = [
    r"suicid",
    r"kill\s+self",
    r"overdose",
    r"psychosis",
    r"schizophren",
    r"bipolar",
    r"depress",
    r"substance",
    r"heroin",
    r"methadone",
    r"cocaine",
    r"relapse",
    r"diazepam",
    r"haloperidol",
]


class SmsNotificationService:
    """Institutional SMS delivery service with mandatory clinical de-identification."""

    def __init__(self, provider: NotificationProvider | None = None):
        if provider:
            self.provider = provider
        else:
            provider_type = getattr(settings, "SMS_PROVIDER", "mock").lower()
            if provider_type == "africastalking":
                self.provider = AfricasTalkingProvider()
            else:
                self.provider = mock_provider

    @staticmethod
    def sanitize_message(message: str, alert_reference: str | None = None) -> str:
        """Enforces that no sensitive clinical diagnosis or notes leak via unencrypted SMS."""
        for pattern in PROHIBITED_SMS_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                logger.warning(
                    f"Sensitive clinical terminology intercepted in SMS text! Masking to privacy standard. Ref: {alert_reference}"
                )
                ref_str = f" Reference: {alert_reference}." if alert_reference else ""
                return (
                    f"Critical ReHUB clinical alert requires immediate review. "
                    f"Please sign in to the secure institutional portal.{ref_str}"
                )
        return message

    async def send_crisis_alert_sms(
        self,
        phone_number: str,
        alert_reference: str,
        urgency: str = "CRITICAL",
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Sends an un-compromised, sanitized SMS notification for high-risk clinical crisis."""
        message = (
            f"URGENT: ReHUB {urgency} clinical alert requires immediate review. "
            f"Please sign in to the secure system immediately. Reference: {alert_reference}"
        )
        # Extra safety check
        safe_message = self.sanitize_message(message, alert_reference=alert_reference)
        return await self.provider.send(
            recipient=phone_number,
            subject=f"ReHUB Clinical Alert: {alert_reference}",
            message=safe_message,
            context=context or {"alert_reference": alert_reference, "channel": "SMS"},
        )

    async def send_sms(
        self,
        phone_number: str,
        message: str,
        subject: str = "ReHUB Notification",
        alert_reference: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """General sanitized SMS sending method."""
        safe_message = self.sanitize_message(message, alert_reference=alert_reference)
        return await self.provider.send(
            recipient=phone_number,
            subject=subject,
            message=safe_message,
            context=context or {"channel": "SMS"},
        )
