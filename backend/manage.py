"""Operational commands. Run from backend/:

    python manage.py migrate                 apply database migrations (same as: alembic upgrade head)
    python manage.py create-admin USERNAME   create an administrator, or promote an existing account

create-admin prompts for the new account's password; set ADMIN_PASSWORD to run it non-interactively.
"""

import argparse
import getpass
import os
import sys


def migrate() -> int:
    from app import db_migrate

    db_migrate.upgrade()
    print("Database schema is up to date.")
    return 0


def create_admin(username: str) -> int:
    from pydantic import ValidationError

    from app.common.exceptions import BusinessException
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.user_service import ensure_admin

    with SessionLocal() as db:
        password = None
        if db.query(User).filter(User.username == username).first() is None:
            password = os.environ.get("ADMIN_PASSWORD")
            if not password:
                password = getpass.getpass("Password for the new administrator: ")
                if password != getpass.getpass("Repeat the password: "):
                    print("The passwords do not match.", file=sys.stderr)
                    return 1
        try:
            outcome = ensure_admin(db, username, password)
        except ValidationError as exc:
            print("; ".join(error["msg"].removeprefix("Value error, ") for error in exc.errors()), file=sys.stderr)
            return 1
        except BusinessException as exc:
            print(exc.message, file=sys.stderr)
            return 1
    print(f"Administrator '{username}': {outcome}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Course schedule operational commands.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="Apply database migrations.")
    admin = commands.add_parser("create-admin", help="Create an administrator or promote an existing account.")
    admin.add_argument("username")
    args = parser.parse_args(argv)
    return migrate() if args.command == "migrate" else create_admin(args.username)


if __name__ == "__main__":
    sys.exit(main())
