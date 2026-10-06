from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.security import password_hasher, permission_codes
from app.models.identity import AuditEvent, AuthSession, Permission, Role, User, utcnow


def test_authentication_cookie_security_and_logout(logged_in, db):
    assert logged_in.get("/api/v1/auth/me").status_code == 200
    assert "clinical.view" not in logged_in.get("/api/v1/auth/me").json()["permissions"]
    assert logged_in.post("/api/v1/auth/logout").status_code == 200
    assert logged_in.get("/api/v1/auth/me").status_code == 401
    assert (
        db.scalar(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "auth.logout")
        )
        == 1
    )


def test_login_cookie_flags(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.org", "password": "ChangeMe!2026"}
    )
    cookies = response.headers.get_list("set-cookie")
    assert any("access_token=" in c and "HttpOnly" in c and "SameSite=strict" in c for c in cookies)
    assert any("refresh_token=" in c and "HttpOnly" in c for c in cookies)
    assert "password_hash" not in response.text


def test_csrf_and_origin_checks(logged_in):
    logged_in.headers.pop("X-CSRF-Token")
    assert logged_in.post("/api/v1/auth/logout").status_code == 403
    assert (
        logged_in.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://evil.example"},
            json={"email": "admin@example.org", "password": "ChangeMe!2026"},
        ).status_code
        == 403
    )


def test_refresh_rotates_and_rejects_replay(logged_in):
    old = logged_in.cookies.get("refresh_token")
    assert logged_in.post("/api/v1/auth/refresh").status_code == 200
    assert logged_in.cookies.get("refresh_token") != old
    logged_in.cookies.clear()
    logged_in.cookies.set("refresh_token", old)
    assert logged_in.post("/api/v1/auth/refresh").status_code == 401


def test_lockout_records_failures(client, db):
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login", json={"email": "admin@example.org", "password": "wrong"}
        )
        assert response.status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "admin@example.org", "password": "ChangeMe!2026"}
        ).status_code
        == 401
    )
    user = db.scalar(select(User).where(User.email == "admin@example.org"))
    assert user.failed_logins == 5 and user.locked_until is not None


def test_idle_timeout(logged_in, db):
    session = db.scalar(select(AuthSession).where(AuthSession.revoked.is_(False)))
    session.last_seen = utcnow() - timedelta(minutes=31)
    db.commit()
    assert logged_in.get("/api/v1/users").status_code == 401
    assert logged_in.post("/api/v1/auth/refresh").status_code == 401


def test_user_create_update_duplicate_and_revocation(logged_in, db):
    roles = logged_in.get("/api/v1/roles?page_size=100").json()["items"]
    read_only = next(r for r in roles if r["name"] == "Read Only User")
    payload = {
        "email": "sample@example.org",
        "full_name": "Sample Staff",
        "password": "Temporary!2026",
        "role_ids": [read_only["id"]],
    }
    response = logged_in.post("/api/v1/users", json=payload)
    assert response.status_code == 201, response.text
    user = response.json()
    assert user["force_password_change"] and "password_hash" not in user
    assert logged_in.post("/api/v1/users", json=payload).status_code == 409
    edit = {
        "full_name": "Sample Staff",
        "active": False,
        "force_password_change": True,
        "role_ids": [read_only["id"]],
        "reason": "Staff departure",
    }
    assert logged_in.put(f"/api/v1/users/{user['id']}", json=edit).status_code == 200
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "user.updated"))
    assert event.previous_values["active"] is True and event.new_values["active"] is False
    assert event.reason == "Staff departure"


def test_force_password_change_and_password_change_revoke_sessions(client, db):
    admin = db.scalar(select(User).where(User.email == "admin@example.org"))
    temporary_password = "ReplacementTemporary!2026"
    admin.password_hash = password_hasher.hash(temporary_password)
    admin.force_password_change = True
    db.commit()
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": admin.email, "password": temporary_password}
        ).status_code
        == 200
    )
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")
    assert client.get("/api/v1/users").status_code == 403
    rejected = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "ChangeMe!2026", "new_password": "MyNewPassword!2026"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["message"] == "Current password is incorrect"
    db.refresh(admin)
    assert admin.force_password_change
    assert password_hasher.verify(temporary_password, admin.password_hash)
    assert client.get("/api/v1/auth/me").status_code == 200
    assert db.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.action == "auth.password_changed")
    ) == 0
    # A second login creates another session that the successful change must also revoke.
    assert client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": temporary_password}
    ).status_code == 200
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")
    assert (
        client.post(
            "/api/v1/auth/change-password",
            json={"current_password": temporary_password, "new_password": "MyNewPassword!2026"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me").status_code == 401
    db.refresh(admin)
    assert not admin.force_password_change
    assert db.scalar(
        select(func.count()).select_from(AuthSession).where(
            AuthSession.user_id == admin.id, AuthSession.revoked.is_(False)
        )
    ) == 0
    assert client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": temporary_password}
    ).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": admin.email, "password": "MyNewPassword!2026"}
        ).status_code
        == 200
    )


def test_server_permission_enforcement(logged_in, db):
    admin = db.scalar(select(User).where(User.email == "admin@example.org"))
    admin.roles = []
    db.commit()
    assert logged_in.get("/api/v1/users").status_code == 403
    assert logged_in.get("/api/v1/audit").status_code == 403
    assert logged_in.get("/api/v1/dashboard").json()["counts"] == {}


def test_ict_cannot_grant_clinical_permissions(logged_in, db):
    clinical = db.scalar(select(Permission).where(Permission.code == "clinical.view"))
    response = logged_in.post(
        "/api/v1/roles",
        json={
            "name": "Escalated Role",
            "permission_ids": [str(clinical.id)],
            "reason": "Attempt escalation",
        },
    )
    assert response.status_code == 403
    assert (
        logged_in.post(
            "/api/v1/users",
            json={
                "email": "escalated@example.org",
                "full_name": "Escalation Attempt",
                "password": "Temporary!2026",
                "permission_ids": [str(clinical.id)],
            },
        ).status_code
        == 403
    )
    for role in db.scalars(
        select(Role).where(
            Role.name.in_(["Super Administrator", "System Administrator", "Facility Administrator"])
        )
    ):
        assert not any(
            p.code.startswith(("clinical.", "psychotherapy.", "therapy.")) for p in role.permissions
        )


def test_cannot_deactivate_self(logged_in):
    user = logged_in.get("/api/v1/auth/me").json()
    response = logged_in.put(
        f"/api/v1/users/{user['id']}",
        json={
            "full_name": user["full_name"],
            "active": False,
            "force_password_change": False,
            "role_ids": [r["id"] for r in user["roles"]],
            "reason": "Deactivate self",
        },
    )
    assert response.status_code == 409


def test_reset_is_one_time_and_generic(client, db, monkeypatch):
    captured = []
    monkeypatch.setattr("app.services.mail.send_reset", lambda email, token: captured.append(token))
    first = client.post("/api/v1/auth/request-reset", json={"email": "admin@example.org"})
    unknown = client.post("/api/v1/auth/request-reset", json={"email": "unknown@example.org"})
    assert first.json() == unknown.json() and len(captured) == 1
    payload = {"token": captured[0], "new_password": "ResetPassword!2026"}
    assert client.post("/api/v1/auth/reset-password", json=payload).status_code == 200
    assert client.post("/api/v1/auth/reset-password", json=payload).status_code == 400
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.org", "password": payload["new_password"]},
        ).status_code
        == 200
    )


def test_audit_database_immutability(logged_in, db):
    logged_in.get("/api/v1/users")
    event = db.scalar(select(AuditEvent).limit(1))
    for sql in (
        "UPDATE audit_events SET action = 'tampered' WHERE id = :id",
        "DELETE FROM audit_events WHERE id = :id",
    ):
        with pytest.raises(DBAPIError), db.begin_nested():
            db.execute(text(sql), {"id": event.id})
    assert logged_in.delete(f"/api/v1/audit/{event.id}").status_code == 404


def test_pagination_search_settings_and_departments(logged_in):
    response = logged_in.get("/api/v1/users?page=1&page_size=1&q=Development")
    assert response.json()["meta"]["total"] == 1
    assert logged_in.get("/api/v1/users?page_size=101").status_code == 422
    created = logged_in.post(
        "/api/v1/departments",
        json={"name": "Quality Assurance", "description": "Quality and safety"},
    )
    assert created.status_code == 201
    assert (
        logged_in.put(
            f"/api/v1/departments/{created.json()['id']}",
            json={"name": "Quality Assurance", "active": False},
        ).status_code
        == 200
    )
    facility = logged_in.get("/api/v1/settings").json()
    facility["short_name"] = "ARS Test"
    assert logged_in.put("/api/v1/settings", json=facility).status_code == 200
    facility["logo_url"] = "javascript:alert(1)"
    assert logged_in.put("/api/v1/settings", json=facility).status_code == 422


def test_direct_permissions_and_role_management(logged_in, db):
    permission = db.scalar(select(Permission).where(Permission.code == "audit.view"))
    role = logged_in.post(
        "/api/v1/roles",
        json={
            "name": "Quality Auditor",
            "permission_ids": [str(permission.id)],
            "reason": "Quality review",
        },
    )
    assert role.status_code == 201
    assert (
        logged_in.put(
            f"/api/v1/roles/{role.json()['id']}",
            json={"name": "Quality Auditor", "permission_ids": [], "reason": "Scope revised"},
        ).status_code
        == 200
    )
    admin = db.scalar(select(User).where(User.email == "admin@example.org"))
    admin.roles = []
    admin.permissions = [permission]
    db.commit()
    assert permission_codes(admin) == {"audit.view"}
    assert logged_in.get("/api/v1/audit").status_code == 200
    assert logged_in.get("/api/v1/users").status_code == 403
