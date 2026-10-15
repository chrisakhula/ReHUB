"""Mock and testing notification provider."""

import logging
from typing import Any

from app.notifications.base import NotificationProvider

logger = logging.getLogger("rehub.notifications.mock")


class MockNotificationProvider(NotificationProvider):
    """In-memory mock provider for automated tests and local development."""

    def __init__(self):
        self.sent_messages: list[dict[str, Any]] = []

    async def send(self, recipient: str, subject: str, message: str, context: dict[str, Any] | None = None) -> bool:
        record = {
            "recipient": recipient,
            "subject": subject,
            "message": message,
            "context": context or {},
        }
        self.sent_messages.append(record)
        logger.info(f"[MOCK_NOTIFICATION] To: {recipient} | Subject: {subject} | Msg: {message}")
        return True

    def clear(self):
        self.sent_messages.clear()


# Default singleton for test assertions
mock_provider = MockNotificationProvider()
