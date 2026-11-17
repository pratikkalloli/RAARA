"""Secure interactive command to create the first administrator account."""

from __future__ import annotations

import getpass
import sys

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.db import SessionLocal
from app.database.models import User
from app.schemas.auth import RegisterRequest
from app.services.security import hash_password


def main() -> int:
    with SessionLocal() as session:
        try:
            if session.bind is not None and session.bind.dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except SQLAlchemyError:
            print("Bootstrap failed: database operation could not be completed.", file=sys.stderr)
            return 1
        if session.scalar(select(User.id).where(User.role == "admin")) is not None:
            print("Bootstrap refused: an administrator account already exists.", file=sys.stderr)
            return 1

        username = input("Admin username: ")
        email = input("Admin email: ")
        password = getpass.getpass("Admin password (12–128 characters): ")
        confirmation = getpass.getpass("Confirm admin password: ")
        if password != confirmation:
            print("Bootstrap failed: passwords did not match.", file=sys.stderr)
            return 1

        try:
            validated = RegisterRequest(username=username, email=email, password=password)
        except ValidationError as exc:
            print("Bootstrap failed: supplied account details are invalid.", file=sys.stderr)
            for error in exc.errors(include_input=False):
                print(f"- {'/'.join(str(part) for part in error['loc'])}: {error['msg']}", file=sys.stderr)
            return 1

        existing = session.scalar(
            select(User.id).where(
                (User.username == validated.username) | (User.email == validated.email)
            )
        )
        if existing is not None:
            print("Bootstrap failed: username or email is already registered.", file=sys.stderr)
            return 1

        session.add(
            User(
                username=validated.username,
                email=validated.email,
                password_hash=hash_password(validated.password),
                role="admin",
                is_active=True,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            print("Bootstrap failed: username or email is already registered.", file=sys.stderr)
            return 1
        except SQLAlchemyError:
            session.rollback()
            print("Bootstrap failed: database operation could not be completed.", file=sys.stderr)
            return 1

    print("Administrator account created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
