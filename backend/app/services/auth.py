import hmac
import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.config import get_settings
from app.core.permissions import aware
from app.core.security import DUMMY_HASH, access_token, digest, password_hasher
from app.models.identity import AuthSession, PasswordReset, User, utcnow
from app.repositories.identity import IdentityRepository


class AuthService:
    def __init__(self, db: Session, request: Request):
        self.db, self.request = db, request
        self.repo = IdentityRepository(db)

    def cookies(
        self, response: Response, user: User, session: AuthSession, refresh: str, csrf: str
    ):
        settings = get_settings()
        common = {"secure": settings.cookie_secure, "samesite": "strict", "path": "/api/v1"}
        response.set_cookie(
            "access_token",
            access_token(str(user.id), str(session.id)),
            httponly=True,
            max_age=settings.access_token_expire_minutes * 60,
            **common,
        )
        response.set_cookie(
            "refresh_token",
            refresh,
            httponly=True,
            max_age=settings.refresh_token_expire_days * 86400,
            **common,
        )
        response.set_cookie(
            "csrf_token",
            csrf,
            httponly=False,
            secure=settings.cookie_secure,
            samesite="strict",
            path="/",
            max_age=settings.refresh_token_expire_days * 86400,
        )

    def login(self, data, response):
        user = self.repo.by_email(str(data.email), lock=True)
        valid = password_hasher.verify(data.password, user.password_hash if user else DUMMY_HASH)
        locked = bool(user and user.locked_until and aware(user.locked_until) > utcnow())
        if not user or not valid or not user.active or locked:
            if user and not locked:
                user.failed_logins += 1
                if user.failed_logins >= 5:
                    user.locked_until = utcnow() + timedelta(minutes=15)
            audit(self.db, self.request, "auth.login_failed", "user", actor=user)
            # Failure counters and security audit survive the rejected request.
            self.db.commit()
            raise HTTPException(401, "Invalid credentials or account unavailable")
        user.failed_logins, user.locked_until, user.last_login = 0, None, utcnow()
        refresh, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        session = AuthSession(
            user_id=user.id,
            refresh_hash=digest(refresh),
            csrf_hash=digest(csrf),
            expires_at=utcnow() + timedelta(days=get_settings().refresh_token_expire_days),
        )
        self.db.add(session)
        self.db.flush()
        self.cookies(response, user, session, refresh, csrf)
        audit(self.db, self.request, "auth.login", "user", user, user.id)
        return user

    def refresh(self, response):
        token = self.request.cookies.get("refresh_token", "")
        session = self.db.scalar(
            select(AuthSession).where(AuthSession.refresh_hash == digest(token)).with_for_update()
        )
        if (
            not session
            or session.revoked
            or aware(session.expires_at) <= utcnow()
            or aware(session.last_seen) + timedelta(minutes=get_settings().session_idle_minutes)
            <= utcnow()
        ):
            raise HTTPException(401, "Session expired. Please sign in.")
        csrf = self.request.headers.get("X-CSRF-Token", "")
        if not csrf or not hmac.compare_digest(session.csrf_hash, digest(csrf)):
            raise HTTPException(403, "Invalid CSRF token")
        user = self.repo.require(User, session.user_id)
        if not user.active:
            raise HTTPException(401, "Account unavailable")
        refresh, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        session.refresh_hash, session.csrf_hash, session.last_seen = (
            digest(refresh),
            digest(csrf),
            utcnow(),
        )
        self.cookies(response, user, session, refresh, csrf)
        audit(self.db, self.request, "auth.refresh", "session", user, session.id)
        return user

    def revoke_all(self, user_id: UUID):
        self.db.execute(
            update(AuthSession).where(AuthSession.user_id == user_id).values(revoked=True)
        )

    def change_password(self, user, data):
        if not password_hasher.verify(data.current_password, user.password_hash):
            raise HTTPException(400, "Current password is incorrect")
        if password_hasher.verify(data.new_password, user.password_hash):
            raise HTTPException(422, "Choose a different password")
        user.password_hash = password_hasher.hash(data.new_password)
        user.force_password_change = False
        self.revoke_all(user.id)
        audit(self.db, self.request, "auth.password_changed", "user", user, user.id)

    def request_reset(self, email):
        user = self.repo.by_email(str(email))
        if not user or not user.active:
            return
        recent = self.db.scalar(
            select(PasswordReset.id).where(
                PasswordReset.user_id == user.id,
                PasswordReset.created_at > utcnow() - timedelta(minutes=2),
            )
        )
        if recent:
            return
        token = secrets.token_urlsafe(48)
        self.db.add(
            PasswordReset(
                user_id=user.id,
                token_hash=digest(token),
                expires_at=utcnow() + timedelta(minutes=30),
            )
        )
        audit(self.db, self.request, "auth.reset_requested", "user", entity_id=user.id)
        from app.services.mail import send_reset

        send_reset(user.email, token)

    def reset_password(self, data):
        record = self.db.scalar(
            select(PasswordReset)
            .where(PasswordReset.token_hash == digest(data.token))
            .with_for_update()
        )
        if not record or record.used or aware(record.expires_at) <= utcnow():
            raise HTTPException(400, "Reset link is invalid or expired")
        user = self.repo.require(User, record.user_id)
        if not user.active:
            raise HTTPException(400, "Reset link is invalid or expired")
        user.password_hash = password_hasher.hash(data.new_password)
        user.force_password_change, user.failed_logins, user.locked_until = False, 0, None
        self.db.execute(
            update(PasswordReset).where(PasswordReset.user_id == user.id).values(used=True)
        )
        self.revoke_all(user.id)
        audit(self.db, self.request, "auth.password_reset", "user", user, user.id)
