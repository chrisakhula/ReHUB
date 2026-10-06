import base64
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.clients import Client
from app.models.identity import Facility, User, utcnow
from app.models.medication import DrugBatch
from app.tests.test_care_workflows import (
    admitted as admitted_fixture,
)
from app.tests.test_care_workflows import (
    post,
)
from app.tests.test_care_workflows import (
    prescription as prescription_fixture,
)

admitted = admitted_fixture
prescription = prescription_fixture


def test_consent_authorised_family_communication_and_withdrawal(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    cid = admitted["client"]["id"]
    now = utcnow()
    contact = post(
        clinical_client,
        f"/clients/{cid}/contacts",
        {
            "kind": "AUTHORIZED_FAMILY",
            "name": "Synthetic Relative",
            "relationship": "Parent",
            "phone": "0700000000",
            "authorized_contact": True,
        },
    )
    consent = post(
        clinical_client,
        f"/admissions/{aid}/consents",
        {
            "consent_type": "FAMILY_COMMUNICATION",
            "consent_text": "Share only agreed recovery progress",
            "version": "1",
            "decision": "GRANTED",
            "consent_date": now.isoformat(),
            "witness": "Synthetic Witness",
        },
    )
    payload = {
        "admission_id": aid,
        "contact_id": contact["id"],
        "consent_id": consent["id"],
        "communicated_at": utcnow().isoformat(),
        "method": "PHONE",
        "purpose": "Synthetic family meeting",
        "shared_information": "Synthetic agreed progress",
        "scope_confirmed": True,
    }
    post(clinical_client, "/rehabilitation/family-communications", payload)
    post(clinical_client, f"/consents/{consent['id']}/withdraw", {"reason": "Synthetic withdrawal"})
    payload["communicated_at"] = utcnow().isoformat()
    assert (
        clinical_client.post(
            "/api/v1/rehabilitation/family-communications", json=payload
        ).status_code
        == 422
    )


def test_group_attendance_private_observations_and_programme(clinical_client, admitted, db):
    aid = admitted["admission"]["id"]
    user = clinical_client.get("/api/v1/auth/me").json()
    now = utcnow()
    group = post(
        clinical_client,
        "/rehabilitation/groups",
        {
            "title": "Synthetic group",
            "session_type": "GROUP_COUNSELLING",
            "topic": "Synthetic topic",
            "facilitator_id": user["id"],
            "start_at": now.isoformat(),
            "duration_minutes": 30,
            "location": "Synthetic room",
            "objectives": "Synthetic objectives",
        },
    )
    post(
        clinical_client,
        f"/rehabilitation/groups/{group['id']}/attendance",
        {
            "admission_id": aid,
            "status": "PRESENT",
            "private_observation": "Restricted synthetic observation",
        },
    )
    person = db.get(User, UUID(user["id"]))
    person.permissions = [p for p in person.permissions if not p.code.startswith("psychotherapy.")]
    db.commit()
    response = clinical_client.get(f"/api/v1/rehabilitation/groups/{group['id']}/attendance").json()
    assert "private_observation" not in response["items"][0]
    activity = post(
        clinical_client,
        "/rehabilitation/programme",
        {
            "title": "Synthetic programme",
            "category": "Life skills",
            "start_at": now.isoformat(),
            "duration_minutes": 30,
            "recurrence": "DAILY",
            "repeat_until": (now.date() + timedelta(days=7)).isoformat(),
            "location": "Synthetic room",
            "facilitator_id": user["id"],
        },
    )
    post(
        clinical_client,
        f"/rehabilitation/programme/{activity['id']}/attendance",
        {"admission_id": aid, "occurrence_date": now.date().isoformat(), "status": "PRESENT"},
    )
    assert (
        clinical_client.get(f"/api/v1/rehabilitation/programme/{activity['id']}/attendance").json()[
            "meta"
        ]["total"]
        == 1
    )


def test_nursing_observation_handover_and_toxicology(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    now = utcnow()
    post(
        clinical_client,
        "/nursing/notes",
        {
            "admission_id": aid,
            "noted_at": now.isoformat(),
            "shift": "DAY",
            "assessment": "Synthetic assessment",
            "note": "Synthetic nursing note",
            "high_risk": True,
            "observation_due_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    post(
        clinical_client,
        "/nursing/observations",
        {
            "admission_id": aid,
            "observed_at": now.isoformat(),
            "appetite": "GOOD",
            "mood": "Calm",
            "hygiene": "INDEPENDENT",
            "sleep_hours": 7,
            "next_observation_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    handover = post(
        clinical_client,
        "/nursing/handovers",
        {
            "admission_id": aid,
            "shift_date": now.date().isoformat(),
            "shift": "DAY",
            "summary": "Synthetic shift summary",
        },
    )
    post(clinical_client, f"/nursing/handovers/{handover['id']}/acknowledge", {})
    assert (
        clinical_client.post(f"/api/v1/nursing/handovers/{handover['id']}/acknowledge").status_code
        == 409
    )
    dashboard = clinical_client.get("/api/v1/nursing/dashboard?page_size=1").json()
    assert dashboard["meta"]["total"] == 1 and len(dashboard["high_risk"]) == 1
    post(
        clinical_client,
        "/toxicology/tests",
        {
            "admission_id": aid,
            "test_at": utcnow().isoformat(),
            "reason": "Synthetic test",
            "sample_type": "Synthetic sample",
            "results": [{"substance": "Synthetic analyte", "result": "NEGATIVE"}],
            "acknowledgement": "ACKNOWLEDGED",
            "follow_up_action": "Synthetic follow-up",
        },
    )
    assert (
        len(clinical_client.get(f"/api/v1/toxicology/trends?admission_id={aid}").json()["items"])
        == 1
    )


def test_private_referral_pdf_client_photo_and_version_history(clinical_client, admitted):
    cid = admitted["client"]["id"]
    referral = clinical_client.get("/api/v1/referrals").json()["items"][0]
    from io import BytesIO

    from PIL import Image
    from pypdf import PdfWriter

    document_bytes = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(document_bytes)
    pdf = document_bytes.getvalue()
    document = post(
        clinical_client,
        f"/referrals/{referral['id']}/documents",
        {"filename": "synthetic.pdf", "content_base64": base64.b64encode(pdf).decode()},
    )
    assert "content" not in document
    response = clinical_client.get(f"/api/v1/intake/documents/{document['id']}")
    assert response.content == pdf and response.headers["content-type"] == "application/pdf"
    assert (
        clinical_client.post(
            f"/api/v1/referrals/{referral['id']}/documents",
            json={"filename": "bad.pdf", "content_base64": base64.b64encode(b"not a pdf").decode()},
        ).status_code
        == 422
    )
    photo = post(
        clinical_client,
        f"/clients/{cid}/photo",
        {
            "filename": "synthetic.jpg",
            "content_base64": (
                lambda stream: (
                    Image.new("RGB", (8, 8), "white").save(stream, format="JPEG"),
                    base64.b64encode(stream.getvalue()).decode(),
                )[1]
            )(BytesIO()),
        },
    )
    assert clinical_client.get(f"/api/v1/clients/{cid}").json()["photo_reference"] == photo["id"]
    assert clinical_client.get(f"/api/v1/clients/{cid}/history").json()["meta"]["total"] == 1


def test_prn_interval_and_allergy_review(clinical_client, admitted, prescription, db):
    rx = prescription["rx"]
    cid = admitted["client"]["id"]
    client = db.get(Client, UUID(cid))
    client.allergies = ["Synthetic medicine"]
    db.commit()
    payload = {
        key: rx[key]
        for key in [
            "admission_id",
            "medication_id",
            "dose",
            "dose_unit",
            "route_id",
            "frequency",
            "start_at",
            "indication",
        ]
    }
    payload.update(
        prn=True,
        prn_min_interval_hours=6,
        scheduled_times=[],
        frequency="PRN synthetic instruction",
    )
    assert clinical_client.post("/api/v1/medication/prescriptions", json=payload).status_code == 409
    order = post(
        clinical_client,
        "/medication/prescriptions",
        {**payload, "allergy_override_reason": "Synthetic clinician review"},
    )
    order = post(
        clinical_client,
        f"/medication/prescriptions/{order['id']}/status",
        {"status": "ACTIVE", "expected_version": 1, "reason": "Synthetic reviewed activation"},
    )
    data = {
        "prescription_id": order["id"],
        "actual_dose": "1",
        "administered_at": utcnow().isoformat(),
        "status": "PRN",
    }
    post(clinical_client, "/medication/administrations", data)
    data["administered_at"] = utcnow().isoformat()
    assert clinical_client.post("/api/v1/medication/administrations", json=data).status_code == 409


def test_history_database_update_and_delete_rejected(clinical_client, admitted, prescription, db):
    for table in ["clinical_encounters", "prescription_revisions", "client_revisions"]:
        if table == "clinical_encounters":
            post(
                clinical_client,
                "/clinical/encounters",
                {
                    "admission_id": admitted["admission"]["id"],
                    "encounter_at": utcnow().isoformat(),
                    "presenting_complaint": "Synthetic original",
                },
            )
        with pytest.raises(DBAPIError), db.begin_nested():
            db.execute(text(f"UPDATE {table} SET updated_at = now()"))
        with pytest.raises(DBAPIError), db.begin_nested():
            db.execute(text(f"DELETE FROM {table}"))


def test_patient_boundaries_and_discontinued_orders(clinical_client, admitted, prescription, db):
    other = Facility(name="Another synthetic facility")
    db.add(other)
    db.flush()
    patient = Client(
        facility_id=other.id,
        client_number="OTHER-001",
        first_name="Separate",
        surname="Person",
        date_of_birth=utcnow().date(),
        sex="UNSPECIFIED",
    )
    db.add(patient)
    db.commit()
    assert clinical_client.get(f"/api/v1/clients/{patient.id}").status_code == 404
    assert clinical_client.get(f"/api/v1/care/options?selected_id={uuid4()}").status_code == 404
    rx = prescription["rx"]
    post(
        clinical_client,
        f"/medication/prescriptions/{rx['id']}/status",
        {
            "status": "DISCONTINUED",
            "expected_version": rx["version"],
            "reason": "Synthetic discontinuation",
        },
    )
    assert (
        clinical_client.post(
            "/api/v1/medication/administrations",
            json={
                "prescription_id": rx["id"],
                "actual_dose": "1",
                "administered_at": utcnow().isoformat(),
                "status": "GIVEN",
            },
        ).status_code
        == 409
    )


def test_expired_batches_cannot_be_dispensed(clinical_client, prescription, db):
    batch = post(
        clinical_client,
        "/pharmacy/batches",
        {
            "medication_id": prescription["med"]["id"],
            "batch_number": "EXPIRE-SYN",
            "expiry_date": (utcnow().date() + timedelta(days=1)).isoformat(),
            "quantity": "5",
            "unit": "tablet",
            "receipt_reference": "SYNTHETIC",
        },
    )
    record = db.get(DrugBatch, UUID(batch["id"]))
    record.expiry_date = utcnow().date() - timedelta(days=1)
    db.commit()
    response = clinical_client.post(
        "/api/v1/pharmacy/movements",
        json={
            "batch_id": batch["id"],
            "movement_type": "DISPENSE",
            "prescription_id": prescription["rx"]["id"],
            "quantity": "1",
            "reason": "Synthetic expired dispensing attempt",
        },
    )
    assert response.status_code == 409 and record.quantity == 5
