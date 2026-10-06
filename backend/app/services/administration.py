from fastapi import HTTPException
from sqlalchemy import select

from app.audit.service import audit
from app.core.security import password_hasher, permission_codes
from app.models.identity import Department, Permission, Role, User
from app.repositories.identity import IdentityRepository
from app.schemas.identity import user_out
from app.services.auth import AuthService


class AdministrationService:
    def __init__(self, db, request, actor):
        self.db, self.request, self.actor = db, request, actor
        self.repo = IdentityRepository(db)

    def grantable(self, permissions):
        if any(p.code not in permission_codes(self.actor) for p in permissions):
            raise HTTPException(403, "You cannot grant permissions you do not hold")

    def user(self, record_id):
        user = self.repo.require(User, record_id)
        if user.facility_id != self.actor.facility_id:
            raise HTTPException(404, "Record not found")
        return user

    def assignments(self, data, preserve_existing=False):
        roles = self.repo.resolve(Role, data.role_ids)
        permissions = self.repo.resolve(Permission, data.permission_ids)
        if not preserve_existing:
            self.grantable(permissions + [p for r in roles for p in r.permissions])
        if data.department_id:
            department = self.repo.require(Department, data.department_id)
            if not department.active:
                raise HTTPException(422, "Select an active department")
        return roles, permissions

    def create_user(self, data):
        if self.repo.by_email(str(data.email)):
            raise HTTPException(409, "An account with this email already exists")
        roles, permissions = self.assignments(data)
        user = User(
            email=str(data.email).lower(),
            full_name=data.full_name,
            password_hash=password_hasher.hash(data.password),
            roles=roles,
            permissions=permissions,
            department_id=data.department_id,
            facility_id=self.actor.facility_id,
            created_by=self.actor.id,
        )
        self.db.add(user)
        self.db.flush()
        audit(
            self.db,
            self.request,
            "user.created",
            "user",
            self.actor,
            user.id,
            new=user_out(user).model_dump(mode="json"),
        )
        return user

    def update_user(self, record_id, data):
        user = self.user(record_id)
        # Account lifecycle changes do not confer access to the user's clinical records.
        # Changes to roles or direct permissions still enforce the grant ceiling.
        unchanged = {r.id for r in user.roles} == set(data.role_ids) and {
            p.id for p in user.permissions
        } == set(data.permission_ids)
        if not unchanged:
            self.grantable(user.permissions + [p for r in user.roles for p in r.permissions])
        roles, permissions = self.assignments(data, preserve_existing=unchanged)
        if user.id == self.actor.id and (
            not data.active
            or "users.manage"
            not in {p.code for p in permissions + [p for r in roles for p in r.permissions]}
        ):
            raise HTTPException(
                409, "You cannot deactivate or remove your own user-management access"
            )
        previous = user_out(user).model_dump(mode="json")
        user.full_name, user.active = data.full_name.strip(), data.active
        user.force_password_change = data.force_password_change
        user.roles, user.permissions, user.department_id = roles, permissions, data.department_id
        user.updated_by = self.actor.id
        AuthService(self.db, self.request).revoke_all(user.id)
        audit(
            self.db,
            self.request,
            "user.updated",
            "user",
            self.actor,
            user.id,
            previous=previous,
            new=user_out(user).model_dump(mode="json"),
            reason=data.reason,
        )
        return user

    def save_role(self, data, record_id=None):
        permissions = self.repo.resolve(Permission, data.permission_ids)
        self.grantable(permissions)
        role = self.repo.require(Role, record_id) if record_id else Role(created_by=self.actor.id)
        previous = None
        if record_id:
            self.grantable(role.permissions)
            previous = {"name": role.name, "permissions": [p.code for p in role.permissions]}
            if any(r.id == role.id for r in self.actor.roles) and "roles.manage" not in {
                p.code for p in permissions
            }:
                raise HTTPException(409, "Cannot remove role-management access from your own role")
        duplicate = self.db.scalar(select(Role).where(Role.name == data.name.strip()))
        if duplicate and duplicate.id != role.id:
            raise HTTPException(409, "A role with this name already exists")
        role.name, role.description = data.name.strip(), data.description
        role.permissions, role.updated_by = permissions, self.actor.id
        if record_id:
            from app.models.identity import user_roles

            for user_id in self.db.scalars(
                select(user_roles.c.user_id).where(user_roles.c.role_id == role.id)
            ):
                AuthService(self.db, self.request).revoke_all(user_id)
        self.db.add(role)
        self.db.flush()
        audit(
            self.db,
            self.request,
            "role.updated" if record_id else "role.created",
            "role",
            self.actor,
            role.id,
            previous=previous,
            new={"name": role.name, "permissions": [p.code for p in permissions]},
            reason=data.reason,
        )
        return role

    def save_department(self, data, record_id=None):
        department = (
            self.repo.require(Department, record_id)
            if record_id
            else Department(created_by=self.actor.id)
        )
        previous = {"name": department.name, "active": department.active} if record_id else None
        duplicate = self.db.scalar(select(Department).where(Department.name == data.name.strip()))
        if duplicate and duplicate.id != department.id:
            raise HTTPException(409, "A department with this name already exists")
        department.name, department.description, department.active = (
            data.name.strip(),
            data.description,
            data.active,
        )
        department.updated_by = self.actor.id
        self.db.add(department)
        self.db.flush()
        audit(
            self.db,
            self.request,
            "department.saved",
            "department",
            self.actor,
            department.id,
            previous=previous,
            new={"name": department.name, "active": department.active},
        )
        return department
