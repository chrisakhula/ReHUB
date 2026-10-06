import hashlib
import secrets
from datetime import timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.models.identity import utcnow

password_hasher = PasswordHash.recommended()
# Equal-cost verification for unknown email addresses.
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def access_token(user_id: str, session_id: str) -> str:
    settings = get_settings()
    now = utcnow()
    return jwt.encode(
        {
            "sub": user_id,
            "sid": session_id,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.secret_key,
        algorithm="HS256",
    )


def permission_codes(user) -> set[str]:
    return {p.code for p in user.permissions} | {p.code for r in user.roles for p in r.permissions}
