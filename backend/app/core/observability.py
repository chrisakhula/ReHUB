"""Observability, health probes, and optional external error tracking integration."""

import logging
import os
import time
from typing import Any, Dict, Tuple
from sqlalchemy import text
from app.core.config import get_settings
from app.core.database import engine

logger = logging.getLogger("ars.observability")


def init_error_tracking() -> None:
    """Initializes external error tracking (e.g. Sentry) if DSN is configured.

    Operates cleanly without throwing errors if the SDK is not installed or DSN is absent.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        logger.info("External error monitoring: disabled (no SENTRY_DSN configured)")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=get_settings().environment,
            traces_sample_rate=0.2,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        logger.info("External error monitoring: Sentry initialized successfully")
    except ImportError:
        logger.warning("SENTRY_DSN provided but sentry-sdk package not installed. Skipping.")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def check_database() -> Tuple[bool, str]:
    """Probes PostgreSQL database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "healthy"
    except Exception as e:
        return False, f"database unavailable: {str(e)[:100]}"


def check_redis() -> Tuple[bool, str]:
    """Probes Redis connectivity."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis
        client = redis.Redis.from_url(redis_url, socket_timeout=2)
        client.ping()
        return True, "healthy"
    except Exception as e:
        # If in dev without Redis running, log status
        return False, f"redis unreachable: {str(e)[:100]}"
