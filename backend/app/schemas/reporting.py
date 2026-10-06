from datetime import datetime
from typing import Optional, List
import uuid
from pydantic import BaseModel, ConfigDict

class ReportingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pass

class ReportingCreate(ReportingBase):
    pass

class ReportingResponse(ReportingBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
