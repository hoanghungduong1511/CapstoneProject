"""Create or promote a local administrator account.

Examples:
    python scripts/create_admin.py --email admin@skinai.com --name "SkinAI Admin"

    ADMIN_EMAIL=admin@skinai.com ADMIN_PASSWORD="strong-password" \
        python scripts/create_admin.py
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a new admin account or promote an existing user.",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("ADMIN_EMAIL"),
        help="Admin email. Defaults to ADMIN_EMAIL.",
    )
    parser.add_argument(
        "--name",
        default=os.getenv("ADMIN_NAME", "SkinAI Administrator"),
        help="Admin display name. Defaults to ADMIN_NAME.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ADMIN_PASSWORD"),
        help="Admin password. Prefer ADMIN_PASSWORD or the hidden prompt.",
    )
    return parser.parse_args()


def get_password(password: str | None) -> str:
    if password is None:
        password = getpass.getpass("Admin password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise ValueError("Password confirmation does not match.")

    if len(password) < 8:
        raise ValueError("Admin password must contain at least 8 characters.")

    return password


def create_or_promote_admin(email: str, name: str, password: str) -> str:
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("A valid admin email is required.")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == normalized_email).first()

        if user is None:
            user = User(
                email=normalized_email,
                name=name.strip() or "SkinAI Administrator",
                password_hash=hash_password(password),
                provider="local",
                role="admin",
                status="active",
            )
            db.add(user)
            action = "created"
        else:
            user.role = "admin"
            user.status = "active"
            user.password_hash = hash_password(password)
            if name.strip():
                user.name = name.strip()
            action = "promoted"

        db.commit()
        db.refresh(user)
        return f"Admin {action}: {user.email} (id={user.id})"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    args = parse_args()

    try:
        if not args.email:
            raise ValueError("Provide --email or set ADMIN_EMAIL.")

        password = get_password(args.password)
        print(create_or_promote_admin(args.email, args.name, password))
        return 0
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Failed to create admin: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
