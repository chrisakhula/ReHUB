import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_reset(email: str, token: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        # No token or email in logs; tests inject delivery. Configure SMTP to enable delivery.
        logger.warning("password_reset_delivery_unconfigured")
        return
    message = EmailMessage()
    message["Subject"] = "ARS RMS password reset"
    message["From"], message["To"] = settings.smtp_from, email
    message.set_content(
        "Reset your password within 30 minutes:\n"
        f"{settings.public_app_url}/reset-password#token={token}\n"
        "If you did not request this, ignore this message."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.error("password_reset_delivery_failed")
