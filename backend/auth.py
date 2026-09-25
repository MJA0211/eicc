import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db import get_db
from backend.models import AuthSession

password_hash = PasswordHash.recommended()


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(db: Session, response: Response, actor: str, role: str):
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=digest(token),
            csrf_token=csrf,
            actor=actor,
            role=role,
            expires_at=datetime.now(UTC) + timedelta(hours=settings().session_hours),
        )
    )
    db.commit()
    response.set_cookie(
        "eicc_session",
        token,
        httponly=True,
        secure=settings().secure_cookies,
        samesite="strict",
        max_age=settings().session_hours * 3600,
        path="/",
    )
    return {"actor": actor, "role": role, "csrf_token": csrf, "demo_mode": settings().demo_mode}


def current_session(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("eicc_session", "")
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(token))) if token else None
    if not session or session.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        raise HTTPException(401, "Sign in to continue")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(supplied, session.csrf_token):
            raise HTTPException(403, "CSRF verification failed")
        origin = request.headers.get("origin")
        if origin and origin not in settings().allowed_origins:
            raise HTTPException(403, "Origin is not allowed")
    return session


def require_role(session, *roles):
    if session.role != "admin" and session.role not in roles:
        raise HTTPException(403, "Your role cannot perform this action")


def writer(session=Depends(current_session)):
    require_role(session, "analyst", "tester", "manager", "stakeholder")
    return session
