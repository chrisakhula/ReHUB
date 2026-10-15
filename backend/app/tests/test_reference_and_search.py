"""Unit and integration tests for Reference Code Generator and Global Quick Search."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.reference_generator import generate_reference_code, next_sequence_value
from app.models.billing import Invoice
from app.models.clients import Admission, Client
from app.models.identity import Facility, Permission, Role, User
from app.models.medication import Medication
from app.models.residential import Incident


def test_reference_code_formats(db: Session):
    facility = db.scalars(select(Facility)).first()
    assert facility is not None

    # Timeless formats (e.g. ARS-00001, MED-00001)
    client_code = generate_reference_code(db, facility.id, "CLIENT")
    assert client_code.startswith("ARS-")
    assert len(client_code) == 9  # ARS-XXXXX

    med_code = generate_reference_code(db, facility.id, "MEDICATION")
    assert med_code.startswith("MED-")
    assert len(med_code) == 9

    # Year-based formats (e.g. ADM-2026-00001, RX-2026-0001)
    adm_code = generate_reference_code(db, facility.id, "ADMISSION", target_year=2026)
    assert adm_code.startswith("ADM-2026-")

    rx_code = generate_reference_code(db, facility.id, "PRESCRIPTION", target_year=2026)
    assert rx_code.startswith("RX-2026-")

    inc_code = generate_reference_code(db, facility.id, "INCIDENT", target_year=2026)
    assert inc_code.startswith("INC-2026-")


def test_reference_code_consecutive_increments(db: Session):
    facility = db.scalars(select(Facility)).first()

    code1 = generate_reference_code(db, facility.id, "STOCK_ITEM")
    code2 = generate_reference_code(db, facility.id, "STOCK_ITEM")

    assert code1 != code2
    num1 = int(code1.split("-")[1])
    num2 = int(code2.split("-")[1])
    assert num2 == num1 + 1


def test_quick_search_endpoint_permissions(client, db: Session):
    # Admin has search permissions
    facility = db.scalars(select(Facility)).first()

    # Create synthetic test client
    test_client = Client(
        facility_id=facility.id,
        client_number="ARS-99991",
        first_name="Wanjiku",
        surname="Kariuki",
        date_of_birth=datetime(1990, 5, 12).date(),
        sex="Female",
        phone="+254712349991",
    )
    db.add(test_client)
    db.commit()

    # Log in as admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.org", "password": "ChangeMe!2026"},
    )
    assert login_res.status_code == 200
    csrf = client.cookies.get("csrf_token")
    client.headers["X-CSRF-Token"] = csrf

    # Search for "Wanjiku"
    res = client.get("/api/v1/search/quick?q=Wanjiku")
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert "total_matches" in data

    # Unauthenticated search is blocked
    unauth_client = client.__class__(client.app)
    unauth_res = unauth_client.get("/api/v1/search/quick?q=Wanjiku")
    assert unauth_res.status_code == 401


def test_concurrent_reference_generation(test_engine):
    """Verifies that concurrent requests generate strictly unique reference codes without collisions."""
    import concurrent.futures
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    fac_id = uuid.uuid4()
    with test_engine.connect() as conn:
        trans = conn.begin()
        conn.execute(
            text(
                "INSERT INTO facilities (id, name, short_name, system_name, created_at, updated_at) "
                "VALUES (:id, :name, :short_name, :sname, now(), now())"
            ),
            {"id": fac_id, "name": "Concurrency Test Facility", "short_name": "CTF", "sname": "ARS RMS"},
        )
        trans.commit()

    SessionLocal = sessionmaker(bind=test_engine)

    try:
        def generate(kind: str, year: int | None = None):
            with SessionLocal() as s:
                code = generate_reference_code(s, fac_id, kind, target_year=year)
                s.commit()
                return code

        kinds_to_test = [
            ("CLIENT", None),
            ("ADMISSION", 2026),
            ("MEDICATION", None),
            ("PRESCRIPTION", 2026),
            ("INCIDENT", 2026),
            ("INVOICE", 2026),
        ]

        for kind, yr in kinds_to_test:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(generate, kind, yr) for _ in range(15)]
                results = [f.result() for f in futures]

            # All 15 generated codes must be strictly unique
            assert len(results) == 15
            assert len(set(results)) == 15, f"Collisions detected in {kind}: {results}"
    finally:
        with test_engine.connect() as conn:
            trans = conn.begin()
            conn.execute(text("DELETE FROM record_numbers WHERE facility_id = :id"), {"id": fac_id})
            conn.execute(text("DELETE FROM facilities WHERE id = :id"), {"id": fac_id})
            trans.commit()

