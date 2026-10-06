from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.clients import Admission
from app.models.identity import AuditEvent, User, utcnow
from app.models.medication import DrugBatch, MedicationAdministration


def post(client, path, payload):
    response = client.post("/api/v1" + path, json=payload)
    assert response.status_code in {200, 201}, response.text
    return response.json()


@pytest.fixture
def admitted(clinical_client):
    client = clinical_client
    now = utcnow()
    person = post(
        client,
        "/clients",
        {
            "first_name": "Synthetic",
            "surname": "Resident",
            "date_of_birth": "1990-03-05",
            "sex": "MALE",
            "national_id": "SYNTHETIC-001",
        },
    )
    referral = post(
        client,
        "/referrals",
        {
            "client_id": person["id"],
            "referral_date": now.date().isoformat(),
            "source": "SELF",
            "reason": "Synthetic intake test",
            "presenting_problem": "Synthetic testing",
        },
    )
    post(
        client,
        f"/referrals/{referral['id']}/screenings",
        {
            "current_intoxication": False,
            "withdrawal_risk": "LOW",
            "suicide_risk": "LOW",
            "self_harm_risk": "LOW",
            "violence_risk": "LOW",
            "psychosis": False,
            "severe_medical_condition": False,
            "pregnancy": False,
            "seizure_history": False,
            "overdose_history": False,
            "accommodation_suitable": True,
            "clinically_suitable": True,
            "decision": "SUITABLE",
            "reason": "Synthetic suitability decision",
        },
    )
    admission = post(
        client,
        "/admissions",
        {
            "client_id": person["id"],
            "referral_id": referral["id"],
            "admission_date": now.isoformat(),
            "reason": "Synthetic admission",
            "programme": "Residential recovery",
            "expected_duration_days": 90,
            "client_rights_acknowledged": True,
            "treatment_agreement": True,
        },
    )
    wing = post(client, "/residential/wings", {"name": "Synthetic Wing"})
    room = post(client, "/residential/rooms", {"wing_id": wing["id"], "name": "Synthetic Room"})
    bed = post(client, "/residential/beds", {"room_id": room["id"], "name": "S01"})
    post(
        client,
        f"/admissions/{admission['id']}/bed",
        {"bed_id": bed["id"], "reason": "Initial synthetic assignment"},
    )
    consent = post(
        client,
        f"/admissions/{admission['id']}/consents",
        {
            "consent_type": "TREATMENT",
            "consent_text": "Synthetic consent text",
            "version": "1",
            "decision": "GRANTED",
            "consent_date": utcnow().isoformat(),
            "witness": "Synthetic Witness",
        },
    )
    admission = post(
        client,
        f"/admissions/{admission['id']}/status",
        {"status": "ACTIVE", "reason": "Synthetic activation"},
    )
    return {"client": person, "admission": admission, "bed": bed, "consent": consent}


def test_registry_screening_admission_activation_and_duplicates(clinical_client, admitted):
    person, admission = admitted["client"], admitted["admission"]
    assert person["client_number"].startswith("ARS-") and admission["status"] == "ACTIVE"
    response = clinical_client.post(
        "/api/v1/clients",
        json={
            "first_name": "Duplicate",
            "surname": "Person",
            "date_of_birth": "1991-01-01",
            "sex": "MALE",
            "national_id": "SYNTHETIC-001",
        },
    )
    assert response.status_code == 409
    assert (
        clinical_client.post(
            f"/api/v1/admissions/{admission['id']}/status",
            json={"status": "DISCHARGED", "reason": "Attempt premature discharge"},
        ).status_code
        == 409
    )
    assert clinical_client.get("/api/v1/clients?q=SYNTHETIC-001").json()["meta"]["total"] == 1
    assert (
        clinical_client.get("/api/v1/care/options").json()["admissions"][0]["id"] == admission["id"]
    )


def test_admission_requires_consent_and_bed(clinical_client, admitted, db):
    admission = db.get(Admission, UUID(admitted["admission"]["id"]))
    admission.status = "PENDING"
    admission.client_rights_acknowledged = False
    db.commit()
    assert (
        clinical_client.post(
            f"/api/v1/admissions/{admission.id}/status",
            json={"status": "ACTIVE", "reason": "Missing rights acknowledgement"},
        ).status_code
        == 409
    )


def test_bed_conflicts_and_transfer_history(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    assert (
        clinical_client.post(
            f"/api/v1/admissions/{aid}/bed",
            json={"bed_id": admitted["bed"]["id"], "reason": "Duplicate bed assignment"},
        ).status_code
        == 409
    )
    room_id = admitted["bed"]["room_id"]
    newbed = post(clinical_client, "/residential/beds", {"room_id": room_id, "name": "S02"})
    post(
        clinical_client,
        f"/admissions/{aid}/bed",
        {"bed_id": newbed["id"], "reason": "Synthetic transfer"},
    )
    history = clinical_client.get(f"/api/v1/admissions/{aid}/bed-history").json()["items"]
    assert len(history) == 2 and sum(row["ended_at"] is None for row in history) == 1
    assert clinical_client.get("/api/v1/residential/occupancy").json()["occupied"] == 1


def test_assessment_scoring_versions_and_treatment_history(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    actor = clinical_client.get("/api/v1/auth/me").json()["id"]
    instrument = post(
        clinical_client,
        "/rehabilitation/instruments",
        {
            "code": "SYNTHETIC",
            "name": "Synthetic scoring example",
            "questions": [
                {
                    "key": "q1",
                    "text": "Synthetic question",
                    "options": [
                        {"value": "no", "label": "No", "score": 0},
                        {"value": "yes", "label": "Yes", "score": 1},
                    ],
                }
            ],
            "score_bands": [
                {
                    "minimum": 0,
                    "maximum": 0,
                    "interpretation": "Synthetic lower band",
                    "risk_level": "LOW",
                },
                {
                    "minimum": 1,
                    "maximum": 1,
                    "interpretation": "Synthetic upper band",
                    "risk_level": "HIGH",
                },
            ],
        },
    )
    result = post(
        clinical_client,
        "/rehabilitation/scores",
        {
            "admission_id": aid,
            "instrument_id": instrument["id"],
            "responses": {"q1": "yes"},
            "completed_at": utcnow().isoformat(),
        },
    )
    assert result["score"] == 1 and result["risk_level"] == "HIGH"
    assert (
        clinical_client.post(
            "/api/v1/rehabilitation/scores",
            json={
                "admission_id": aid,
                "instrument_id": instrument["id"],
                "responses": {},
                "completed_at": utcnow().isoformat(),
            },
        ).status_code
        == 422
    )
    today = utcnow().date()
    target = today + timedelta(days=30)
    payload = {
        "admission_id": aid,
        "presenting_problem": "Synthetic presentation",
        "problem_area": "Recovery",
        "goal": "Synthetic recovery goal",
        "objectives": [
            {
                "description": "Attend programme",
                "measure": "Attendance record",
                "intervention": "Structured programme",
                "target_date": target.isoformat(),
            }
        ],
        "responsible_professional_id": actor,
        "start_date": today.isoformat(),
        "target_date": target.isoformat(),
        "review_date": (today + timedelta(days=7)).isoformat(),
        "status": "ACTIVE",
    }
    first = post(clinical_client, "/rehabilitation/treatment-plans", payload)
    second = post(
        clinical_client,
        "/rehabilitation/treatment-plans",
        {
            **payload,
            "supersedes_id": first["id"],
            "correction_reason": "Synthetic review",
            "status": "UNDER_REVIEW",
        },
    )
    assert second["version"] == 2
    assert (
        clinical_client.get(
            f"/api/v1/rehabilitation/treatment-plans?admission_id={aid}&current_only=false"
        ).json()["meta"]["total"]
        == 2
    )


def test_psychotherapy_confidentiality(clinical_client, admitted, db):
    actor = clinical_client.get("/api/v1/auth/me").json()["id"]
    now = utcnow()
    session = post(
        clinical_client,
        "/rehabilitation/sessions",
        {
            "admission_id": admitted["admission"]["id"],
            "session_type": "INDIVIDUAL_COUNSELLING",
            "therapist_id": actor,
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(hours=1)).isoformat(),
            "objective": "Synthetic session",
            "summary": "Confidential synthetic content",
            "intervention": "Synthetic intervention",
            "confidential": True,
            "status": "SCHEDULED",
        },
    )
    user = db.get(User, UUID(actor))
    user.permissions = [p for p in user.permissions if not p.code.startswith("psychotherapy.")]
    db.commit()
    assert clinical_client.get("/api/v1/rehabilitation/sessions").json()["items"] == []
    assert (
        clinical_client.get(f"/api/v1/rehabilitation/sessions/{session['id']}").status_code == 403
    )


def test_encounter_revisions_vitals_and_lab(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    now = utcnow()
    payload = {
        "admission_id": aid,
        "encounter_at": now.isoformat(),
        "presenting_complaint": "Synthetic complaint",
        "diagnosis": "Synthetic problem",
        "plan": "Synthetic plan",
    }
    encounter = post(clinical_client, "/clinical/encounters", payload)
    corrected = post(
        clinical_client,
        f"/clinical/encounters/{encounter['id']}/revisions",
        {
            **payload,
            "presenting_complaint": "Corrected synthetic complaint",
            "expected_version": 1,
            "reason": "Correct transcription",
        },
    )
    assert corrected["version"] == 2
    history = clinical_client.get(
        f"/api/v1/clinical/encounters/{encounter['id']}/revisions"
    ).json()["items"]
    assert history[0]["snapshot"]["presenting_complaint"] == "Synthetic complaint"
    assert (
        clinical_client.post(
            "/api/v1/clinical/vitals",
            json={"admission_id": aid, "observed_at": now.isoformat(), "systolic": 120},
        ).status_code
        == 422
    )
    post(
        clinical_client,
        "/clinical/vitals",
        {"admission_id": aid, "observed_at": now.isoformat(), "systolic": 120, "diastolic": 80},
    )
    lab = post(
        clinical_client,
        "/lab/requests",
        {
            "admission_id": aid,
            "test": "Synthetic external test",
            "indication": "Synthetic reason",
            "provider": "Synthetic lab",
            "specimen_type": "Synthetic sample",
        },
    )
    lab = post(
        clinical_client,
        f"/lab/requests/{lab['id']}/results",
        {"resulted_at": now.isoformat(), "result": "Synthetic result", "abnormal_flag": "NORMAL"},
    )
    result = lab["results"][0]
    reviewed = post(
        clinical_client, f"/lab/results/{result['id']}/review", {"review_note": "Synthetic review"}
    )
    assert reviewed["status"] == "REVIEWED"


@pytest.fixture
def prescription(clinical_client, admitted):
    med = post(
        clinical_client,
        "/medication/catalogue",
        {
            "generic_name": "Synthetic medicine",
            "formulation": "Tablet",
            "strength": "Synthetic strength",
            "dose_unit": "tablet",
            "reorder_level": "10",
        },
    )
    route = next(
        row
        for row in clinical_client.get("/api/v1/medication/routes").json()["items"]
        if row["code"] == "oral"
    )
    now = utcnow()
    start = now
    rx = post(
        clinical_client,
        "/medication/prescriptions",
        {
            "admission_id": admitted["admission"]["id"],
            "medication_id": med["id"],
            "dose": "1",
            "dose_unit": "tablet",
            "route_id": route["id"],
            "frequency": "Once daily synthetic schedule",
            "scheduled_times": [
                (now + timedelta(minutes=1))
                .astimezone(__import__("zoneinfo").ZoneInfo("Africa/Nairobi"))
                .strftime("%H:%M")
            ],
            "start_at": start.isoformat(),
            "indication": "Synthetic test indication",
        },
    )
    rx = post(
        clinical_client,
        f"/medication/prescriptions/{rx['id']}/status",
        {"status": "ACTIVE", "expected_version": 1, "reason": "Synthetic activation"},
    )
    return {
        "rx": rx,
        "med": med,
        "route": route,
        "schedule_date": (now + timedelta(minutes=1))
        .astimezone(__import__("zoneinfo").ZoneInfo("Africa/Nairobi"))
        .date(),
    }


def test_prescribing_scheduling_administration_and_immutable_history(
    clinical_client, admitted, prescription, db
):
    rx = prescription["rx"]
    today = prescription["schedule_date"]
    count = post(
        clinical_client,
        f"/medication/schedule?admission_id={rx['admission_id']}",
        {"start": today.isoformat(), "end": today.isoformat()},
    )
    assert count["doses_created"] == 1
    assert (
        post(
            clinical_client,
            f"/medication/schedule?admission_id={rx['admission_id']}",
            {"start": today.isoformat(), "end": today.isoformat()},
        )["doses_created"]
        == 0
    )
    due = clinical_client.get(f"/api/v1/medication/due?admission_id={rx['admission_id']}").json()[
        "items"
    ][0]
    data = {
        "prescription_id": rx["id"],
        "dose_id": due["id"],
        "actual_dose": "1",
        "administered_at": utcnow().isoformat(),
        "status": "GIVEN",
    }
    admin = post(clinical_client, "/medication/administrations", data)
    assert clinical_client.post("/api/v1/medication/administrations", json=data).status_code == 409
    post(
        clinical_client,
        f"/medication/administrations/{admin['id']}/addenda",
        {"correction": "Synthetic correction", "reason": "Clarify record"},
    )
    assert db.get(MedicationAdministration, UUID(admin["id"])).actual_dose == 1
    history = clinical_client.get(f"/api/v1/medication/prescriptions/{rx['id']}/history").json()[
        "items"
    ]
    assert len(history) == 2


def test_pharmacy_receipt_dispensing_ward_return_count_and_negative_stock(
    clinical_client, prescription, db
):
    batch = post(
        clinical_client,
        "/pharmacy/batches",
        {
            "medication_id": prescription["med"]["id"],
            "batch_number": "SYN-001",
            "expiry_date": (utcnow().date() + timedelta(days=60)).isoformat(),
            "quantity": "20",
            "unit": "tablet",
            "receipt_reference": "SYN-RECEIPT",
        },
    )

    def movement(kind, quantity, **extra):
        return post(
            clinical_client,
            "/pharmacy/movements",
            {
                "batch_id": batch["id"],
                "movement_type": kind,
                "quantity": str(quantity),
                "reason": "Synthetic stock movement",
                **extra,
            },
        )

    movement("DISPENSE", 2, prescription_id=prescription["rx"]["id"])
    movement("WARD_ISSUE", 5, location="Synthetic ward")
    movement("WARD_RETURN", 2, location="Synthetic ward")
    assert db.get(DrugBatch, UUID(batch["id"])).quantity == 15
    failed = clinical_client.post(
        "/api/v1/pharmacy/movements",
        json={
            "batch_id": batch["id"],
            "movement_type": "ADJUST_OUT",
            "quantity": "100",
            "reason": "Synthetic overdraw",
        },
    )
    assert failed.status_code == 409
    assert db.get(DrugBatch, UUID(batch["id"])).quantity == 15
    counted = post(
        clinical_client,
        "/pharmacy/counts",
        {"batch_id": batch["id"], "counted_quantity": "14", "reason": "Synthetic count variance"},
    )
    assert counted["variance"] == "-1.000"


def test_ict_has_no_care_endpoint_access(logged_in):
    for path in [
        "/clients",
        "/admissions",
        "/clinical/encounters",
        "/rehabilitation/sessions",
        "/medication/prescriptions",
        "/pharmacy/batches",
    ]:
        assert logged_in.get("/api/v1" + path).status_code == 403, path


def test_sensitive_audit_does_not_copy_notes(clinical_client, admitted, db):
    marker = "SECRET_SYNTHETIC_NOTE_NOT_FOR_AUDIT"
    post(
        clinical_client,
        "/clinical/encounters",
        {
            "admission_id": admitted["admission"]["id"],
            "encounter_at": utcnow().isoformat(),
            "presenting_complaint": marker,
        },
    )
    events = list(db.scalars(select(AuditEvent)))
    assert all(marker not in str(e.previous_values) + str(e.new_values) for e in events)
