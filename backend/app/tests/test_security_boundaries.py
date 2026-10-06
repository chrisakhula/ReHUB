from datetime import timedelta

from sqlalchemy import select

from app.models.identity import AuditEvent, AuthSession, Facility, PasswordReset, User, utcnow


def test_deactivation_rejects_existing_access_and_refresh(logged_in, db):
    user = db.scalar(select(User).where(User.email == "admin@example.org"))
    user.active = False
    db.commit()
    assert logged_in.get("/api/v1/auth/me").status_code == 401
    assert logged_in.post("/api/v1/auth/refresh").status_code == 401


def test_revoked_access_cookie_cannot_be_replayed(logged_in):
    access = logged_in.cookies.get("access_token")
    assert logged_in.post("/api/v1/auth/logout").status_code == 200
    logged_in.cookies.set("access_token", access)
    assert logged_in.get("/api/v1/auth/me").status_code == 401


def test_facility_scope_on_accounts_and_audit(logged_in, db):
    other = Facility(name="Separate synthetic facility")
    db.add(other)
    db.flush()
    user = User(
        email="other@example.org",
        full_name="Separate Facility Staff",
        password_hash="unused",
        facility_id=other.id,
    )
    db.add(user)
    db.flush()
    db.add(
        AuditEvent(
            user_id=user.id,
            facility_id=other.id,
            action="test.other_facility",
            entity="user",
            entity_id=str(user.id),
        )
    )
    db.commit()
    assert logged_in.get("/api/v1/users?q=Separate").json()["items"] == []
    assert logged_in.get("/api/v1/audit?q=test.other_facility").json()["items"] == []
    response = logged_in.put(
        f"/api/v1/users/{user.id}",
        json={
            "full_name": user.full_name,
            "active": False,
            "force_password_change": True,
            "reason": "Cross-facility attempt",
        },
    )
    assert response.status_code == 404


def test_expired_password_reset_is_rejected(client, db, monkeypatch):
    tokens = []
    monkeypatch.setattr("app.services.mail.send_reset", lambda email, token: tokens.append(token))
    client.post("/api/v1/auth/request-reset", json={"email": "admin@example.org"})
    reset = db.scalar(select(PasswordReset))
    reset.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": tokens[0], "new_password": "NewPassword!2026"},
        ).status_code
        == 400
    )


def test_absolute_session_expiry(logged_in, db):
    session = db.scalar(select(AuthSession))
    session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert logged_in.get("/api/v1/auth/me").status_code == 401
    assert logged_in.post("/api/v1/auth/refresh").status_code == 401


def test_invalid_audit_date_range(logged_in):
    assert (
        logged_in.get(
            "/api/v1/audit?start=2026-10-10T00:00:00Z&end=2026-10-01T00:00:00Z"
        ).status_code
        == 422
    )
