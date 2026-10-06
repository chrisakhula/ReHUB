import pytest
import uuid
from datetime import timedelta
from sqlalchemy import select

from app.models.identity import utcnow
from app.tests.test_care_workflows import post, admitted as admitted_fixture, prescription as prescription_fixture

admitted = admitted_fixture
prescription = prescription_fixture

def test_phase2_referral_status_and_bed_states(clinical_client, admitted):
    # Referral status
    cid = admitted["client"]["id"]
    now = utcnow()
    referral = post(clinical_client, "/referrals", {
        "client_id": cid,
        "referral_date": now.date().isoformat(),
        "source": "SELF",
        "reason": "Test referral",
        "presenting_problem": "Test"
    })
    post(clinical_client, f"/referrals/{referral['id']}/status", {"status": "DEFERRED", "reason": "Testing"})
    assert clinical_client.get(f"/api/v1/referrals/{referral['id']}").json()["status"] == "DEFERRED"

    # Bed states
    bed = post(clinical_client, "/residential/beds", {"room_id": admitted["bed"]["room_id"], "name": "B2_" + uuid.uuid4().hex[:6]})
    post(clinical_client, f"/residential/beds/{bed['id']}/status", {"status": "MAINTENANCE", "reason": "Broken"})
    beds = clinical_client.get(f"/api/v1/residential/beds?room_id={admitted['bed']['room_id']}").json()["items"]
    updated_bed = next(b for b in beds if b["id"] == bed["id"])
    assert updated_bed["status"] == "MAINTENANCE"

def test_phase2_property(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    prop = post(clinical_client, f"/admissions/{aid}/property", {
        "description": "Watch",
        "category": "VALUABLES",
        "quantity": 1,
        "client_acknowledgment": "Signed"
    })
    returned = post(clinical_client, f"/property/{prop['id']}/return", {"reason": "Discharge"})
    assert returned["returned_at"] is not None

def test_phase3_biopsychosocial_and_risk(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    actor = clinical_client.get("/api/v1/auth/me").json()["id"]

    # Biopsychosocial
    bps = post(clinical_client, "/rehabilitation/biopsychosocial", {
        "admission_id": aid,
        "biological": {"health": "good"},
        "psychological": {"mood": "stable"},
        "social": {"family": "supportive"},
        "substance_use": {"alcohol": "none"},
        "legal": {"issues": "none"},
        "occupational": {"job": "employed"},
        "spiritual": {},
        "status": "COMPLETED",
        "correction_reason": ""
    })
    reviewed = post(clinical_client, "/rehabilitation/biopsychosocial", {
        "admission_id": aid,
        "biological": {"health": "good"},
        "psychological": {"mood": "stable"},
        "social": {"family": "supportive"},
        "substance_use": {"alcohol": "none"},
        "legal": {"issues": "none"},
        "occupational": {"job": "employed"},
        "spiritual": {},
        "status": "REVIEWED",
        "supersedes_id": bps["id"],
        "correction_reason": "Looks good"
    })
    assert reviewed["status"] == "REVIEWED"

    # Risk
    risk = post(clinical_client, "/rehabilitation/risks", {
        "admission_id": aid,
        "risk_type": "SUICIDE",
        "level": "CRITICAL",
        "risk_factors": "Prior attempts",
        "intervention": "Constant observation",
        "assigned_staff_id": actor,
        "review_date": (utcnow() + timedelta(days=1)).date().isoformat()
    })
    alerts = clinical_client.get("/api/v1/rehabilitation/risk-alerts").json()
    assert any(a["id"] == risk["id"] for a in alerts["items"])

def test_phase3_substance_history_and_case(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    actor = clinical_client.get("/api/v1/auth/me").json()["id"]

    sub = post(clinical_client, "/rehabilitation/substances", {"name": f"Alcohol_{uuid.uuid4().hex[:6]}"})
    hist = post(clinical_client, "/rehabilitation/substance-histories", {
        "admission_id": aid,
        "substance_id": sub["id"],
        "frequency": "Daily",
        "quantity": "A lot",
        "route": "Oral"
    })
    assert hist["id"] is not None
    
    # Case assignment
    case = post(clinical_client, "/rehabilitation/cases", {
        "admission_id": aid,
        "case_manager_id": actor,
        "counsellor_id": actor,
        "team_member_ids": []
    })
    assert case["case_manager_id"] == actor

def test_phase4_clinical_orders_problems_vitals(clinical_client, admitted):
    aid = admitted["admission"]["id"]
    actor = clinical_client.get("/api/v1/auth/me").json()["id"]

    prob = post(clinical_client, "/clinical/problems", {
        "admission_id": aid,
        "diagnosis": "Hypertension",
        "client_id": admitted["client"]["id"]
    })
    assert prob["id"] is not None

    order = post(clinical_client, "/clinical/orders", {
        "admission_id": aid,
        "order_type": "MEDICAL",
        "description": "Low sodium diet",
        "priority": "ROUTINE"
    })
    assert order["id"] is not None

    # Vital sign range tests
    now = utcnow()
    with pytest.raises(Exception):
        # Missing diastolic without notes
        post(clinical_client, "/clinical/vitals", {
            "admission_id": aid,
            "observed_at": now.isoformat(),
            "systolic": 120
        })

    with pytest.raises(Exception):
        # Systolic <= Diastolic
        post(clinical_client, "/clinical/vitals", {
            "admission_id": aid,
            "observed_at": now.isoformat(),
            "systolic": 80,
            "diastolic": 120
        })

def test_phase5_pharmacy_suppliers_alerts_refused(clinical_client, prescription):
    # Supplier
    sup = post(clinical_client, "/pharmacy/suppliers", {
        "name": f"MedCorp_{uuid.uuid4().hex[:6]}",
        "active": True
    })
    assert sup["id"] is not None

    # Pharmacy Alerts
    alerts = clinical_client.get("/api/v1/pharmacy/alerts").json()
    assert "expiring_batches" in alerts
    assert "low_stock" in alerts

    # Refused dose reason
    now = utcnow()
    pid = prescription["rx"]["id"]
    
    post(
        clinical_client,
        f"/medication/schedule?admission_id={prescription['rx']['admission_id']}",
        {"start": prescription["schedule_date"].isoformat(), "end": prescription["schedule_date"].isoformat()}
    )
    
    doses = clinical_client.get(f"/api/v1/medication/due?admission_id={prescription['rx']['admission_id']}").json()["items"]
    due = next(d for d in doses if d["prescription_id"] == pid)
    
    with pytest.raises(Exception):
        # Refused without reason
        post(clinical_client, "/medication/administrations", {
            "prescription_id": pid,
            "dose_id": due["id"],
            "administered_at": now.isoformat(),
            "status": "REFUSED"
        })
    
    # With reason
    admin = post(clinical_client, "/medication/administrations", {
        "prescription_id": pid,
        "dose_id": due["id"],
        "administered_at": now.isoformat(),
        "status": "REFUSED",
        "reason": "Patient refused due to nausea"
    })
    assert admin["id"] is not None


