"""Abstract interface for multi-channel institutional notification providers."""

from abc import ABC, abstractmethod
from typing import Any


class NotificationProvider(ABC):
    """Abstract provider for sending external alerts (SMS, Email, Webhook, etc.)."""

    @abstractmethod
    async def send(self, recipient: str, subject: str, message: str, context: dict[str, Any] | None = None) -> bool:
        """Send a notification to a specific recipient.

        Args:
            recipient: Phone number (E.164), email address, or user ID.
            subject: Brief title or topic.
            message: Sanctified message body.
            context: Optional tracing or metadata dict.

        Returns:
            bool indicating whether delivery was accepted.
        """
        pass
