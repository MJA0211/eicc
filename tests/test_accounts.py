from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend import models as m
from backend.config import settings
from backend.seed import ensure_organization
from backend.users import create_user


def test_authenticated_mode_password_roles_csrf_expiry_and_no_demo(client, database, monkeypatch):
    monkeypatch.setattr(settings(), "demo_mode", False)
    with database() as db:
        user = create_user(
            db,
            email="Tester@example.test",
            name="Fictional Test Operator",
            role="viewer",
            password="fictional-test-password-only",
        )
        assert user.password_hash != "fictional-test-password-only"
    assert client.post("/api/auth/demo", json={"role": "admin"}).status_code == 404
    assert (
        client.post("/api/auth/login", json={"email": "tester@example.test", "password": "wrong"}).status_code
        == 401
    )
    response = client.post(
        "/api/auth/login", json={"email": "TESTER@example.test", "password": "fictional-test-password-only"}
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    assert client.get("/api/workspace").status_code == 200
    assert (
        client.post("/api/projects", json={"key": "AUTH-TEST", "title": "Forbidden project"}).status_code
        == 403
    )
    with database() as db:
        auth = db.scalar(select(m.AuthSession).where(m.AuthSession.actor == "Fictional Test Operator"))
        auth.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/workspace").status_code == 401


def test_account_provisioning_rejects_weak_password_duplicate_and_keeps_secrets_out_of_audit(database):
    args = {"email": "operator@example.test", "name": "Fictional Operator", "role": "manager"}
    with database() as db:
        with pytest.raises(ValueError, match="12–1024"):
            create_user(db, **args, password="short")
        create_user(db, **args, password="fictional-private-password")
        with pytest.raises(ValueError, match="already exists"):
            create_user(db, **args, password="fictional-private-password")
        event = db.scalar(select(m.AuditLog).where(m.AuditLog.action == "account_created"))
        assert event.new_value == {"email": args["email"], "role": "manager"}
        first = ensure_organization(db)
        assert ensure_organization(db).id == first.id
