import hmac
from datetime import timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import digest, permission_codes
from app.models.identity import AuthSession, User, utcnow


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def current_user(request: Request, db: Session = Depends(get_db, scope="function")) -> User:
    try:
        payload = jwt.decode(
            request.cookies.get("access_token", ""),
            get_settings().secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "sid", "exp", "iat"]},
        )
        if payload.get("type") != "access":
            raise ValueError()
        session = db.get(AuthSession, UUID(payload["sid"]))
        user = db.get(User, UUID(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Session expired. Please sign in.") from None
    if (
        not session
        or not user
        or session.user_id != user.id
        or session.revoked
        or not user.active
        or aware(session.expires_at) <= utcnow()
        or aware(session.last_seen) + timedelta(minutes=get_settings().session_idle_minutes)
        <= utcnow()
    ):
        raise HTTPException(401, "Session expired. Please sign in.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf = request.headers.get("X-CSRF-Token", "")
        if not csrf or not hmac.compare_digest(session.csrf_hash, digest(csrf)):
            raise HTTPException(403, "Invalid CSRF token")
    if user.force_password_change and request.url.path not in {
        "/api/v1/auth/me",
        "/api/v1/auth/change-password",
        "/api/v1/auth/logout",
    }:
        raise HTTPException(403, "Change your password before continuing")
    session.last_seen = utcnow()
    request.state.auth_session = session
    return user


def require_permission(code: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if code not in permission_codes(user):
            raise HTTPException(403, "You do not have permission for this action")
        return user

    return dependency
