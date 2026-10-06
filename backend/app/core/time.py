from datetime import datetime, timezone
from zoneinfo import ZoneInfo

EAT = ZoneInfo("Africa/Nairobi")


def business_today():
    return datetime.now(timezone.utc).astimezone(EAT).date()


def filter_time(value):
    return value.replace(tzinfo=EAT) if value and value.tzinfo is None else value
