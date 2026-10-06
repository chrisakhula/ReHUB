"""Trusted local provisioning of staff without granting ICT clinical read access."""

import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import password_hasher
from app.models.identity import AuditEvent, Facility, Role, User


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", action="append", required=True)
    args = parser.parse_args()
    email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    password = getpass("Initial password (12–128 characters): ")
    if not 12 <= len(password) <= 128 or password != getpass("Confirm password: "):
        raise SystemExit("Passwords must match and contain 12–128 characters")
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("Account already exists")
        roles = list(db.scalars(select(Role).where(Role.name.in_(args.role))))
        if len(roles) != len(set(args.role)):
            raise SystemExit("Choose existing role names; seed references first")
        facility = db.scalar(select(Facility).limit(1))
        if not facility:
            raise SystemExit("Seed the facility first")
        user = User(
            email=email,
            full_name=args.name.strip(),
            facility_id=facility.id,
            password_hash=password_hasher.hash(password),
            roles=roles,
            force_password_change=True,
        )
        db.add(user)
        db.flush()
        db.add(
            AuditEvent(
                user_id=user.id,
                facility_id=user.facility_id,
                action="user.provisioned",
                entity="user",
                entity_id=str(user.id),
                new_values={"role_ids": [str(r.id) for r in roles]},
                reason="Staff roles provisioned through controlled local administration",
            )
        )
        db.commit()
        print("Staff account created. First sign-in requires a password change.")


if __name__ == "__main__":
    main()
