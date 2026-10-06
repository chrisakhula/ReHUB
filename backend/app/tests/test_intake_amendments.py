from sqlalchemy import select

from app.models.identity import utcnow
from app.tests.test_care_workflows import admitted as admitted_fixture
from app.tests.test_care_workflows import post

admitted = admitted_fixture


def test_pending_acknowledgments_can_be_completed(clinical_client, admitted, db):
    from uuid import UUID

    from app.models.clients import Admission

    admission = db.get(Admission, UUID(admitted["admission"]["id"]))
    admission.status = "PENDING"
    admission.client_rights_acknowledged = False
    admission.treatment_agreement = False
    db.commit()
    changed = clinical_client.put(
        f"/api/v1/admissions/{admission.id}/intake",
        json={
            "client_rights_acknowledged": True,
            "treatment_agreement": True,
            "reason": "Complete verified acknowledgments",
        },
    )
    assert changed.status_code == 200, changed.text
    post(
        clinical_client,
        f"/admissions/{admission.id}/status",
        {"status": "ACTIVE", "reason": "Activate completed intake"},
    )
    history = clinical_client.get(f"/api/v1/admissions/{admission.id}/intake/history").json()[
        "items"
    ]
    assert len(history) == 2
    assert {row["snapshot"]["client_rights_acknowledged"] for row in history} == {True, False}


def test_future_group_attendance_is_rejected(clinical_client, admitted):
    actor = clinical_client.get("/api/v1/auth/me").json()["id"]
    from datetime import timedelta

    group = post(
        clinical_client,
        "/rehabilitation/groups",
        {
            "title": "Future synthetic group",
            "session_type": "GROUP_COUNSELLING",
            "topic": "Synthetic topic",
            "facilitator_id": actor,
            "start_at": (utcnow() + timedelta(days=1)).isoformat(),
            "duration_minutes": 30,
            "location": "Synthetic room",
            "objectives": "Synthetic objectives",
        },
    )
    assert (
        clinical_client.post(
            f"/api/v1/rehabilitation/groups/{group['id']}/attendance",
            json={"admission_id": admitted["admission"]["id"], "status": "PRESENT"},
        ).status_code
        == 422
    )


def test_zero_variance_stock_count_is_preserved(clinical_client, admitted, db):
    from app.models.medication import PharmacyStockCount

    med = post(
        clinical_client,
        "/medication/catalogue",
        {
            "generic_name": "Synthetic counted item",
            "strength": "Synthetic",
            "formulation": "Tablet",
            "dose_unit": "tablet",
        },
    )
    from datetime import timedelta

    from app.core.time import business_today

    batch = post(
        clinical_client,
        "/pharmacy/batches",
        {
            "medication_id": med["id"],
            "batch_number": "COUNT-SYN",
            "expiry_date": (business_today() + timedelta(days=60)).isoformat(),
            "quantity": "5",
            "unit": "tablet",
            "receipt_reference": "SYNTHETIC",
        },
    )
    post(
        clinical_client,
        "/pharmacy/counts",
        {
            "batch_id": batch["id"],
            "counted_quantity": "5",
            "reason": "Synthetic zero variance count",
        },
    )
    record = db.scalar(select(PharmacyStockCount))
    assert record.variance == 0
    assert clinical_client.get("/api/v1/pharmacy/counts").json()["meta"]["total"] == 1


def test_intake_assignment_appears_without_case_profile(clinical_client, admitted, db):
    from uuid import UUID

    from app.models.clients import Admission

    actor = clinical_client.get("/api/v1/auth/me").json()["id"]
    admission = db.get(Admission, UUID(admitted["admission"]["id"]))
    admission.primary_case_manager_id = UUID(actor)
    db.commit()
    response = clinical_client.get("/api/v1/rehabilitation/case-dashboard").json()
    assert response["meta"]["total"] == 1
    assert response["items"][0]["case_profile_required"] is True


def test_used_medicine_identity_cannot_be_relabelled(clinical_client, admitted):
    med = post(
        clinical_client,
        "/medication/catalogue",
        {
            "generic_name": "Synthetic fixed identity",
            "strength": "Synthetic",
            "formulation": "Tablet",
            "dose_unit": "tablet",
        },
    )
    from datetime import timedelta

    from app.core.time import business_today

    post(
        clinical_client,
        "/pharmacy/batches",
        {
            "medication_id": med["id"],
            "batch_number": "IDENTITY-SYN",
            "expiry_date": (business_today() + timedelta(days=30)).isoformat(),
            "quantity": "5",
            "unit": "tablet",
            "receipt_reference": "SYNTHETIC",
        },
    )
    response = clinical_client.put(
        "/api/v1/medication/catalogue/" + med["id"],
        json={
            "generic_name": med["generic_name"],
            "strength": "Changed identity",
            "formulation": "Tablet",
            "dose_unit": "tablet",
        },
    )
    assert response.status_code == 409
