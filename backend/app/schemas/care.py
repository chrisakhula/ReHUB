from datetime import datetime
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CareModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    facility_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None


class CorrectionIn(CareModel):
    reason: str = Field(min_length=3, max_length=500)


def care_paging(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query("", max_length=100),
    sort: str = "created_at",
    direction: str = "desc",
    start: datetime | None = None,
    end: datetime | None = None,
):
    from app.core.time import filter_time

    start, end = filter_time(start), filter_time(end)
    return {
        "page": page,
        "page_size": page_size,
        "q": q,
        "sort": sort,
        "direction": direction,
        "start": start,
        "end": end,
    }


class TimedRecord(CareModel):
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("A timezone is required")
        return value
