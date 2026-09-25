"""Operator-only account provisioning; passwords never enter command-line arguments."""

import argparse
import getpass
import re

from sqlalchemy import select

from backend import models as m
from backend.auth import password_hash
from backend.db import SessionLocal

ROLES = ("viewer", "analyst", "tester", "stakeholder", "manager", "admin")


def create_user(db, *, email, name, role, password):
    email, name = email.strip().lower(), name.strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 200:
        raise ValueError("Provide a valid email address of at most 200 characters")
    if not name or len(name) > 150 or role not in ROLES:
        raise ValueError("Provide a name of 1–150 characters and an allowed role")
    if len(password) < 12 or len(password) > 1024:
        raise ValueError("Password must contain 12–1024 characters")
    if db.scalar(select(m.User).where(m.User.email == email)):
        raise ValueError("This account already exists; no account was changed")
    user = m.User(email=email, name=name, role=role, password_hash=password_hash.hash(password))
    db.add(user)
    db.flush()
    db.add(
        m.AuditLog(
            actor="Local operator",
            action="account_created",
            entity="users",
            entity_id=user.id,
            new_value={"email": email, "role": role},
        )
    )
    db.commit()
    return user


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=ROLES, required=True)
    args = parser.parse_args()
    password = getpass.getpass("New password (12+ characters): ")
    if password != getpass.getpass("Confirm password: "):
        parser.exit(1, "Passwords do not match; no account was created.\n")
    try:
        with SessionLocal() as db:
            create_user(db, **vars(args), password=password)
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    print("Account created. Sign in using the email and password form.")


if __name__ == "__main__":
    main()
