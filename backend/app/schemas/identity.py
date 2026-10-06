from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Password = Annotated[str, Field(min_length=12, max_length=128)]
Name = Annotated[str, Field(min_length=2, max_length=150)]


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: Password


class ResetRequestIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: Password


class UserCreate(BaseModel):
    email: EmailStr
    full_name: Name
    password: Password
    department_id: UUID | None = None
    role_ids: list[UUID] = Field(default_factory=list, max_length=30)
    permission_ids: list[UUID] = Field(default_factory=list, max_length=200)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Enter a name with at least two characters")
        return value.strip()


class UserUpdate(BaseModel):
    full_name: Name
    active: bool
    force_password_change: bool
    department_id: UUID | None = None
    role_ids: list[UUID] = Field(default_factory=list, max_length=30)
    permission_ids: list[UUID] = Field(default_factory=list, max_length=200)
    reason: str = Field(min_length=3, max_length=500)


class RoleIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(max_length=500, default="")
    permission_ids: list[UUID] = Field(default_factory=list, max_length=200)
    reason: str = Field(min_length=3, max_length=500)


class DepartmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(max_length=500, default="")
    active: bool = True


class FacilityIn(BaseModel):
    name: Name
    system_name: Name
    short_name: str = Field(min_length=2, max_length=30)
    contact_email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=1000)
    logo_url: str | None = Field(default=None, max_length=500)

    @field_validator("logo_url")
    @classmethod
    def safe_logo(cls, value):
        if value and not value.startswith("https://"):
            raise ValueError("Logo must be an HTTPS URL")
        return value


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    description: str


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    permissions: list[PermissionOut]


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    active: bool
    force_password_change: bool
    department_id: UUID | None
    facility_id: UUID
    last_login: datetime | None
    created_at: datetime
    roles: list[RoleOut]
    direct_permissions: list[PermissionOut]
    permissions: list[str]


def user_out(user) -> UserOut:
    from app.core.security import permission_codes

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        active=user.active,
        force_password_change=user.force_password_change,
        department_id=user.department_id,
        facility_id=user.facility_id,
        last_login=user.last_login,
        created_at=user.created_at,
        roles=[RoleOut.model_validate(r) for r in user.roles],
        direct_permissions=[PermissionOut.model_validate(p) for p in user.permissions],
        permissions=sorted(permission_codes(user)),
    )
