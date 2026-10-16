"""Concurrency-safe reference code generator for ReHUB entities.

Generates immutable, human-friendly, unique reference numbers across clinical,
business, financial, and operational records using atomic sequence persistence.
"""

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from app.models.clients import RecordNumber
from app.models.identity import Facility

EAT = ZoneInfo("Africa/Nairobi")

REFERENCE_CONFIG = {
    # Timeless sequences (zero-padded 5 digits)
    "CLIENT": {"prefix": "ARS", "digits": 5, "use_year": False},
    "MEDICATION": {"prefix": "MED", "digits": 5, "use_year": False},
    "STOCK_ITEM": {"prefix": "STK", "digits": 5, "use_year": False},
    "STAFF": {"prefix": "STF", "digits": 4, "use_year": False},
    
    # Year-based sequences (zero-padded 4 or 5 digits)
    "ADMISSION": {"prefix": "ADM", "digits": 5, "use_year": True},
    "REFERRAL": {"prefix": "REF", "digits": 4, "use_year": True},
    "ASSESSMENT": {"prefix": "ASM", "digits": 4, "use_year": True},
    "TREATMENT_PLAN": {"prefix": "TP", "digits": 4, "use_year": True},
    "ENCOUNTER": {"prefix": "ENC", "digits": 4, "use_year": True},
    "PRESCRIPTION": {"prefix": "RX", "digits": 4, "use_year": True},
    "MEDICATION_ORDER": {"prefix": "MO", "digits": 4, "use_year": True},
    "EMAR": {"prefix": "MAR", "digits": 4, "use_year": True},
    "LAB_ORDER": {"prefix": "LAB", "digits": 4, "use_year": True},
    "INCIDENT": {"prefix": "INC", "digits": 4, "use_year": True},
    "CRISIS_ALERT": {"prefix": "CR", "digits": 4, "use_year": True},
    "INVOICE": {"prefix": "INV", "digits": 4, "use_year": True},
    "RECEIPT": {"prefix": "RCT", "digits": 4, "use_year": True},
    "PAYMENT": {"prefix": "PAY", "digits": 4, "use_year": True},
    "EXPENSE": {"prefix": "EXP", "digits": 4, "use_year": True},
    "JOURNAL": {"prefix": "JV", "digits": 4, "use_year": True},
    "SUPPLIER_INVOICE": {"prefix": "SIN", "digits": 4, "use_year": True},
    "PURCHASE_ORDER": {"prefix": "PO", "digits": 4, "use_year": True},
    "DISCHARGE": {"prefix": "DIS", "digits": 4, "use_year": True},
    "AFTERCARE": {"prefix": "AFC", "digits": 4, "use_year": True},
    "VISITOR": {"prefix": "VIS", "digits": 4, "use_year": True},
    "CREDIT_NOTE": {"prefix": "CN", "digits": 4, "use_year": True},
    "WRITE_OFF": {"prefix": "WO", "digits": 4, "use_year": True},
    "CASH_RECONCILIATION": {"prefix": "CRN", "digits": 4, "use_year": True},
    "FINANCIAL_ASSESSMENT": {"prefix": "FAS", "digits": 5, "use_year": True},
    "ESTIMATE": {"prefix": "EST", "digits": 5, "use_year": True},
    "FINANCIAL_AGREEMENT": {"prefix": "FAG", "digits": 5, "use_year": True},
    "PAYMENT_PLAN": {"prefix": "PPL", "digits": 5, "use_year": True},
    "REFUND": {"prefix": "RF", "digits": 5, "use_year": True},
    "RESIDENT_FUND": {"prefix": "RFA", "digits": 5, "use_year": True},
    "DISCHARGE_CLEARANCE": {"prefix": "CLR", "digits": 5, "use_year": True},
    "SPONSOR": {"prefix": "SPN", "digits": 5, "use_year": True},
}


def next_sequence_value(db: Session, facility_id: UUID, kind: str, year: int) -> int:
    """Atomically increments and returns the next sequence counter for (facility_id, kind, year).
    
    Uses PostgreSQL atomic INSERT ... ON CONFLICT DO UPDATE RETURNING to prevent
    race conditions and avoid duplicate sequence values under concurrent requests.
    """
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        stmt = (
            pg_insert(RecordNumber)
            .values(
                facility_id=facility_id,
                kind=kind[:40],
                year=year,
                last_value=1,
            )
            .on_conflict_do_update(
                index_elements=["facility_id", "kind", "year"],
                set_={"last_value": RecordNumber.last_value + 1},
            )
            .returning(RecordNumber.last_value)
        )
        val = db.scalar(stmt)
        db.flush()
        return int(val)
    else:
        # Fallback for SQLite / other test databases: serialize via facility lock
        db.scalar(select(Facility).where(Facility.id == facility_id).with_for_update())
        counter = db.get(RecordNumber, (facility_id, kind[:40], year))
        if counter is None:
            counter = RecordNumber(
                facility_id=facility_id,
                kind=kind[:40],
                year=year,
                last_value=0,
            )
            db.add(counter)
        counter.last_value += 1
        db.flush()
        return counter.last_value


def generate_reference_code(
    db: Session,
    facility_id: UUID,
    entity_kind: str,
    target_year: int | None = None,
) -> str:
    """Generates an immutable, standardized human-readable reference code.
    
    Examples:
        CLIENT -> ARS-00124
        MEDICATION -> MED-00127
        STOCK_ITEM -> STK-00281
        ADMISSION -> ADM-2026-00124
        PRESCRIPTION -> RX-2026-0105
        ENCOUNTER -> ENC-2026-0281
    """
    cfg = REFERENCE_CONFIG.get(entity_kind)
    if not cfg:
        # Default fallback
        prefix = entity_kind[:3].upper()
        digits = 4
        use_year = True
    else:
        prefix = cfg["prefix"]
        digits = cfg["digits"]
        use_year = cfg["use_year"]

    current_year = (
        target_year
        if target_year is not None
        else datetime.now(EAT).year
    )
    counter_year = current_year if use_year else 0
    seq = next_sequence_value(db, facility_id, entity_kind, counter_year)

    if use_year:
        return f"{prefix}-{current_year}-{seq:0{digits}d}"
    else:
        return f"{prefix}-{seq:0{digits}d}"
