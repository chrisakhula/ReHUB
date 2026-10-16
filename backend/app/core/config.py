from decimal import Decimal
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore", hide_input_in_errors=True)
    database_url: str
    secret_key: str = ""
    finance_expense_senior_approval_threshold: Decimal = Decimal("50000.00")
    cash_variance_manager_threshold: Decimal = Decimal("5000.00")
    billing_discount_senior_approval_threshold_percent: Decimal = Decimal("10.00")
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    session_idle_minutes: int = 30
    environment: str = "development"
    backend_cors_origins: list[str] = ["http://localhost:5173"]
    file_storage_path: str = "./storage"
    cookie_secure: bool = False
    public_app_url: str = "http://localhost:5173"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.org"
    smtp_starttls: bool = True
    redis_url: str = "redis://127.0.0.1:6379/0"

    # M-Pesa Daraja Configuration
    mpesa_environment: str = "sandbox"
    mpesa_consumer_key: str = ""
    mpesa_consumer_secret: str = ""
    mpesa_shortcode: str = ""
    mpesa_passkey: str = ""
    mpesa_callback_url: str = ""
    mpesa_timeout_url: str = ""
    mpesa_result_url: str = ""

    # SMS Provider Configuration
    sms_provider: str = "disabled"  # disabled, africastalking, twilio, mock
    sms_api_key: str = ""
    sms_username: str = ""
    sms_sender_id: str = "ReHUB"

    # Observability & Monitoring
    sentry_dsn: str = ""

    @model_validator(mode="after")
    def validate_security(self):
        if len(self.secret_key) < 32 or self.secret_key.startswith("replace-with"):
            raise ValueError("SECRET_KEY must contain at least 32 random characters")
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("Production requires COOKIE_SECURE=true and HTTPS")
        if (
            min(
                self.access_token_expire_minutes,
                self.refresh_token_expire_days,
                self.session_idle_minutes,
            )
            <= 0
        ):
            raise ValueError("Session lifetimes must be positive")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
