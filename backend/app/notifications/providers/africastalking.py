"""Africa's Talking SMS provider adapter."""

import logging
from typing import Any
import httpx

from app.core.config import get_settings
from app.notifications.base import NotificationProvider

logger = logging.getLogger("rehub.notifications.africastalking")
settings = get_settings()


class AfricasTalkingProvider(NotificationProvider):
    """Africa's Talking SMS API gateway integration."""

    def __init__(
        self,
        username: str | None = None,
        api_key: str | None = None,
        sender_id: str | None = None,
    ):
        self.username = username or getattr(settings, "AFRICASTALKING_USERNAME", "sandbox")
        self.api_key = api_key or getattr(settings, "AFRICASTALKING_API_KEY", "")
        self.sender_id = sender_id or getattr(settings, "AFRICASTALKING_SENDER_ID", None)

        if self.username.lower() == "sandbox":
            self.base_url = "https://api.sandbox.africastalking.com/version1/messaging"
        else:
            self.base_url = "https://api.africastalking.com/version1/messaging"

    async def send(
        self,
        recipient: str,
        subject: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        if not self.api_key:
            logger.warning("AfricasTalking API key not configured; skipping SMS transmission.")
            return False

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "apiKey": self.api_key,
        }
        data = {
            "username": self.username,
            "to": recipient,
            "message": message,
        }
        if self.sender_id:
            data["from"] = self.sender_id

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.base_url, headers=headers, data=data)
                if response.status_code in (200, 201):
                    res_json = response.json()
                    recipients = res_json.get("SMSMessageData", {}).get("Recipients", [])
                    if recipients and recipients[0].get("status") in ("Success", "Pending"):
                        logger.info(f"AfricasTalking SMS queued to {recipient}")
                        return True
                    logger.warning(f"AfricasTalking response status not successful: {res_json}")
                    return False
                logger.error(f"AfricasTalking HTTP {response.status_code}: {response.text}")
                return False
        except Exception as exc:
            logger.exception(f"AfricasTalking delivery failure to {recipient}: {exc}")
            return False
