from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict

class LicenceBase(BaseModel):
    name: str
    authority: str
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: str = "active"
    reference_number: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class LicenceCreate(LicenceBase):
    pass

class LicenceResponse(LicenceBase):
    id: uuid.UUID

class AuditRecordBase(BaseModel):
    title: str
    audit_date: Optional[datetime] = None
    auditor: str
    findings: Optional[str] = None
    passed: bool = True
    model_config = ConfigDict(from_attributes=True)

class AuditRecordCreate(AuditRecordBase):
    pass

class AuditRecordResponse(AuditRecordBase):
    id: uuid.UUID
