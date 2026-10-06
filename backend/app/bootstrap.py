"""Create the first real administrator without development credentials."""

import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import password_hasher
from app.models.identity import AuditEvent, Department, Facility, Role, User
from app.seed import seed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    password = getpass("Initial password (12+ characters): ")
    if len(password) < 12 or len(password) > 128 or password != getpass("Confirm password: "):
        raise SystemExit("Passwords must match and contain 12–128 characters")
    with SessionLocal() as db:
        seed(db)
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("Account already exists; bootstrap does not overwrite accounts")
        facility = db.scalar(select(Facility).limit(1))
        role = db.scalar(select(Role).where(Role.name == "System Administrator"))
        department = db.scalar(select(Department).where(Department.name == "Administration"))
        user = User(
            email=email,
            full_name=args.name.strip(),
            password_hash=password_hasher.hash(password),
            facility_id=facility.id,
            department_id=department.id,
            roles=[role],
            force_password_change=True,
        )
        db.add(user)
        db.flush()
        db.add(
            AuditEvent(
                user_id=user.id,
                facility_id=user.facility_id,
                action="user.bootstrapped",
                entity="user",
                entity_id=str(user.id),
                reason="Local administrator bootstrap",
            )
        )
        db.commit()
        print("Administrator created. First sign-in requires a password change.")


if __name__ == "__main__":
    main()
