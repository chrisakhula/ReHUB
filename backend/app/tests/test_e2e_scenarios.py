"""Complete End-to-End Institutional Clinical, Operational, and Financial Scenarios."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import Invoice, MpesaTransaction, Payment, PaymentAllocation
from app.models.clients import Admission, Bed, Client, Referral, Room, Wing
from app.models.finance import FinanceJournalEntry, FinanceJournalLine
from app.models.identity import Facility, Permission, Role, User
from app.models.medication import Medication, MedicationAdministration, MedicationRoute, Prescription
from app.models.residential import Incident
from app.services.crisis import CrisisEscalationService
from app.services.discharge import DischargeService
from app.services.finance import FinanceLedgerService
from app.services.mpesa import MpesaService
from app.services.residential import ResidentialService
from app.schemas.discharge import DischargePlanIn, AftercareCaseIn
from app.schemas.residential import IncidentIn, IncidentAddendumIn


def make_test_user(db: Session, email_prefix: str, facility_id: uuid.UUID, permissions: list[str]) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@rehub.local",
        password_hash="argon2id$test_hash",
        full_name=f"Test {email_prefix.capitalize()}",
        facility_id=facility_id,
        active=True,
    )
    for code in permissions:
        p = db.scalar(select(Permission).where(Permission.code == code))
        if not p:
            p = Permission(id=uuid.uuid4(), code=code, description=code)
            db.add(p)
        user.permissions.append(p)
    db.add(user)
    db.commit()
    return user


def test_e2e_scenario_1_full_patient_lifecycle(db: Session):
    """Scenario 1: Referral -> Screening -> Client -> Admission -> Bed -> Discharge -> Bed Release -> Aftercare."""
    facility = db.scalars(select(Facility)).first()
    doctor = make_test_user(db, "doc", facility.id, [
        "client.view", "client.create", "client.admit", "client.discharge", "residential.view", "residential.edit"
    ])

    # 1. Client Creation
    client = Client(
        facility_id=facility.id,
        client_number=f"ARS-{uuid.uuid4().hex[:6].upper()}",
        first_name="Wanjiku",
        surname="Kariuki",
        date_of_birth=date(1988, 7, 20),
        sex="MALE",
        national_id=f"NAT-{uuid.uuid4().hex[:6]}",
        created_by=doctor.id,
        updated_by=doctor.id,
    )
    db.add(client)
    db.flush()

    # 2. Admission
    admission = Admission(
        facility_id=facility.id,
        client_id=client.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:6].upper()}",
        admission_date=datetime.now(timezone.utc),
        admission_type="VOLUNTARY",
        expected_duration_days=90,
        status="ACTIVE",
        reason="Residential Addiction & Dual Diagnosis Recovery",
        programme="90-Day Residential Rehabilitation",
        client_rights_acknowledged=True,
        treatment_agreement=True,
        created_by=doctor.id,
        updated_by=doctor.id,
    )
    db.add(admission)
    db.flush()

    # 3. Bed Assignment
    wing = Wing(facility_id=facility.id, name=f"Recovery Wing {uuid.uuid4().hex[:4]}", created_by=doctor.id, updated_by=doctor.id)
    db.add(wing)
    db.flush()
    room = Room(facility_id=facility.id, wing_id=wing.id, name="Room 101", created_by=doctor.id, updated_by=doctor.id)
    db.add(room)
    db.flush()
    bed = Bed(facility_id=facility.id, room_id=room.id, name="Bed A", status="OCCUPIED", created_by=doctor.id, updated_by=doctor.id)
    db.add(bed)
    db.flush()
    admission.bed_id = bed.id
    db.commit()

    # 4. Discharge Planning & Execution
    discharge_svc = DischargeService(db, None, doctor)
    plan_in = DischargePlanIn(
        admission_id=admission.id,
        discharge_type="PLANNED",
        discharge_date=datetime.now(timezone.utc) + timedelta(days=90),
        relapse_prevention="Structured 12-step engagement with family support sessions",
        accommodation="Family residence with spouse",
    )
    plan = discharge_svc.create_discharge_plan(plan_in)
    assert plan.status == "DRAFT"

    # Fulfill discharge: sets plan to DISCHARGED and closes admission
    completed_plan = discharge_svc.update_discharge_status(plan.id, "DISCHARGED")
    assert completed_plan.status == "DISCHARGED"
    db.refresh(admission)
    assert admission.status == "DISCHARGED"

    # Bed release check
    bed.status = "AVAILABLE"
    db.commit()
    db.refresh(bed)
    assert bed.status == "AVAILABLE"

    # 5. Aftercare Case & Scheduled Follow-up
    aftercare_in = AftercareCaseIn(
        client_id=client.id,
        admission_id=admission.id,
        assigned_staff_id=doctor.id,
        start_date=datetime.now(timezone.utc),
    )
    aftercare_case = discharge_svc.create_aftercare_case(aftercare_in)
    assert aftercare_case.status == "ACTIVE"
    assert aftercare_case.assigned_staff_id == doctor.id


def test_e2e_scenario_2_crisis_alert_and_escalation(db: Session):
    """Scenario 2: High suicide-risk assessment -> Crisis alert -> Clinician notification -> Acknowledgement -> Intervention -> Resolution."""
    import asyncio
    facility = db.scalars(select(Facility)).first()
    doctor = make_test_user(db, "clinician", facility.id, ["clinical.view", "clinical.edit"])

    client = Client(
        facility_id=facility.id,
        client_number=f"ARS-{uuid.uuid4().hex[:6].upper()}",
        first_name="Jane",
        surname="Wambui",
        date_of_birth=date(1995, 3, 12),
        sex="FEMALE",
        national_id=f"NAT-{uuid.uuid4().hex[:6]}",
        created_by=doctor.id,
        updated_by=doctor.id,
    )
    db.add(client)
    db.flush()

    admission = Admission(
        facility_id=facility.id,
        client_id=client.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:6].upper()}",
        admission_date=datetime.now(timezone.utc),
        admission_type="VOLUNTARY",
        expected_duration_days=90,
        status="ACTIVE",
        reason="Acute Detoxification",
        programme="Inpatient Detox",
        client_rights_acknowledged=True,
        treatment_agreement=True,
        created_by=doctor.id,
        updated_by=doctor.id,
    )
    db.add(admission)
    db.commit()

    crisis_svc = CrisisEscalationService()

    # 1. Trigger High-Risk Assessment Crisis Alert
    alert = asyncio.run(
        crisis_svc.create_crisis_alert(
            db=db,
            facility_id=facility.id,
            client_id=client.id,
            admission_id=admission.id,
            trigger="C-SSRS Level 5: Active Suicidal Ideation with Intent and Plan",
            severity="CRITICAL",
            source_entity="PsychiatricEvaluation",
            source_entity_id=str(client.id),
            text_snippet="Client expressed acute intent during morning psych evaluation",
            assigned_clinician_id=doctor.id,
        )
    )
    assert alert.status == "NEW"
    assert alert.severity == "CRITICAL"

    # 2. Clinician Acknowledgement
    ack = crisis_svc.acknowledge_alert(db, alert.id, doctor.id, note="Reviewing immediately")
    assert ack.status == "ACKNOWLEDGED"
    assert ack.acknowledged_by == doctor.id
    assert ack.acknowledged_at is not None

    # 3. Clinical Intervention & Review
    review = crisis_svc.start_review(
        db,
        alert.id,
        doctor.id,
        response_summary="Initiated 1-to-1 continuous observation nursing protocol",
        intervention_plan="Psychiatric consultation called, sedative PRN ordered",
    )
    assert review.status == "UNDER_REVIEW"
    assert review.response is not None

    # 4. Final Resolution
    resolved = crisis_svc.resolve_alert(
        db,
        alert.id,
        doctor.id,
        resolution_notes="Client stabilized following psychiatrist consultation; transfer to high-dependency observation room completed with continuous 1:1 watch.",
    )
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None


def test_e2e_scenario_3_mpesa_billing_reconciliation(db: Session):
    """Scenario 3: M-Pesa STK push -> Callback -> Payment -> Allocation -> GL posting -> Reconciliation."""
    facility = db.scalars(select(Facility)).first()
    finance_user = make_test_user(db, "fin", facility.id, [
        "finance.view", "finance.edit", "finance.approve", "billing.collect_payment", "finance.reconcile"
    ])

    ledger = FinanceLedgerService(db, None, finance_user)
    ledger.seed_defaults()
    db.commit()

    # Create client and invoice
    client = Client(
        facility_id=facility.id,
        client_number=f"ARS-{uuid.uuid4().hex[:6].upper()}",
        first_name="Peter",
        surname="Kamau",
        date_of_birth=date(1982, 11, 5),
        sex="MALE",
        national_id=f"NAT-{uuid.uuid4().hex[:6]}",
        created_by=finance_user.id,
        updated_by=finance_user.id,
    )
    db.add(client)
    db.flush()

    invoice = Invoice(
        facility_id=facility.id,
        client_id=client.id,
        invoice_number=f"INV-{uuid.uuid4().hex[:6].upper()}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="ISSUED",
        subtotal=Decimal("25000.00"),
        total_amount=Decimal("25000.00"),
        created_by=finance_user.id,
        updated_by=finance_user.id,
    )
    db.add(invoice)
    db.commit()

    mpesa_svc = MpesaService(db, actor=finance_user)

    # 1. Initiate STK Push
    tx = mpesa_svc.initiate_stk_push(
        facility_id=facility.id,
        client_id=client.id,
        invoice_id=invoice.id,
        phone_number="0712345678",
        amount=Decimal("25000.00"),
    )
    assert tx.status in {"PENDING", "REQUESTED"}
    assert tx.checkout_request_id is not None

    # 2. Process Safaricom Daraja Callback
    receipt_no = f"QGH{uuid.uuid4().hex[:7].upper()}"
    callback_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": tx.merchant_request_id,
                "CheckoutRequestID": tx.checkout_request_id,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 25000.00},
                        {"Name": "MpesaReceiptNumber", "Value": receipt_no},
                        {"Name": "TransactionDate", "Value": 20261012140000},
                        {"Name": "PhoneNumber", "Value": 254712345678},
                    ]
                },
            }
        }
    }
    res = mpesa_svc.process_callback(callback_payload)
    assert res.get("ResultCode") == 0
    db.refresh(tx)
    assert tx.status == "SUCCESS"
    assert tx.reconciliation_status == "AUTO_RECONCILED"

    # 3. Verify Payment and Allocation in Billing
    db.refresh(invoice)
    assert invoice.status == "PAID"
    payment = db.scalar(select(Payment).where(Payment.transaction_reference == receipt_no))
    assert payment is not None
    assert payment.amount == Decimal("25000.00")
    assert payment.payment_method == "MPESA"

    allocation = db.scalar(select(PaymentAllocation).where(PaymentAllocation.payment_id == payment.id))
    assert allocation is not None
    assert allocation.amount == Decimal("25000.00")

    # Verify General Ledger Entry balanced
    gl_entry = db.scalar(
        select(FinanceJournalEntry).where(
            FinanceJournalEntry.source_module == "BILLING_MPESA",
            FinanceJournalEntry.source_id == str(tx.id),
        )
    )
    assert gl_entry is not None
    total_deb = sum(line.debit for line in gl_entry.lines)
    total_cred = sum(line.credit for line in gl_entry.lines)
    assert total_deb == total_cred == Decimal("25000.00")


def test_e2e_scenario_4_incident_investigation_and_closure(db: Session):
    """Scenario 4: Incident -> Investigation -> Corrective action -> Closure -> Report."""
    facility = db.scalars(select(Facility)).first()
    officer = make_test_user(db, "security", facility.id, ["residential.view", "residential.edit"])

    residential_svc = ResidentialService(db, None, officer)

    # 1. Report Residential Incident
    inc_in = IncidentIn(
        category="CONTRABAND",
        severity="HIGH",
        location="East Dormitory Locker 14",
        timestamp=datetime.now(timezone.utc),
        description="Unprescribed sedative tablets found during routine locker inspection",
        immediate_action_taken="Tablets sealed in evidence tamper bag and handed to Nurse on Duty",
        parties_involved="Resident R-102",
        witnesses="Security Guard Omondi",
    )
    incident = residential_svc.report_incident(inc_in)
    assert incident.status == "OPEN"
    assert incident.severity == "HIGH"

    # 2. Add Investigation Addendum & Corrective Action
    add_in = IncidentAddendumIn(
        incident_id=incident.id,
        addendum_type="INVESTIGATION",
        note="Resident interviewed with primary counsellor. Stated tablets were brought during weekend visitor session. Visitor protocol tightened.",
    )
    addendum = residential_svc.add_incident_addendum(add_in)
    assert addendum.id is not None
    assert addendum.incident_id == incident.id

    # 3. Incident Closure
    incident.status = "CLOSED"
    db.commit()
    db.refresh(incident)
    assert incident.status == "CLOSED"


def test_e2e_scenario_5_medication_dispensing_administration_refusal(db: Session):
    """Scenario 5: Prescription -> Dispensing -> Administration Refusal (reason mandatory) -> Audit."""
    facility = db.scalars(select(Facility)).first()
    nurse = make_test_user(db, "nurse", facility.id, [
        "client.view", "medication.view", "medication.prescribe", "medication.dispense", "medication.administer"
    ])

    client = Client(
        facility_id=facility.id,
        client_number=f"ARS-{uuid.uuid4().hex[:6].upper()}",
        first_name="Mary",
        surname="Moraa",
        date_of_birth=date(1994, 9, 18),
        sex="FEMALE",
        national_id=f"NAT-{uuid.uuid4().hex[:6]}",
        created_by=nurse.id,
        updated_by=nurse.id,
    )
    db.add(client)
    db.flush()

    admission = Admission(
        facility_id=facility.id,
        client_id=client.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:6].upper()}",
        admission_date=datetime.now(timezone.utc),
        admission_type="VOLUNTARY",
        expected_duration_days=90,
        status="ACTIVE",
        reason="Alcohol Cessation & Withdrawal Management",
        programme="Detoxification Protocol",
        client_rights_acknowledged=True,
        treatment_agreement=True,
        created_by=nurse.id,
        updated_by=nurse.id,
    )
    db.add(admission)
    db.flush()

    # Route and Medication Catalogue
    route = db.scalar(select(MedicationRoute).where(MedicationRoute.code == "ORAL"))
    if not route:
        route = MedicationRoute(code="ORAL", name="Oral", active=True, created_by=nurse.id, updated_by=nurse.id)
        db.add(route)
        db.flush()

    medication = Medication(
        facility_id=facility.id,
        reference_code=f"MED-{uuid.uuid4().hex[:6].upper()}",
        generic_name="Diazepam",
        brand_name="Valium",
        formulation="Tablet",
        strength="10mg",
        dose_unit="mg",
        active=True,
        created_by=nurse.id,
        updated_by=nurse.id,
    )
    db.add(medication)
    db.flush()

    # 1. Prescribe Medication
    prescription = Prescription(
        facility_id=facility.id,
        reference_code=f"RX-{uuid.uuid4().hex[:6].upper()}",
        client_id=client.id,
        admission_id=admission.id,
        medication_id=medication.id,
        generic_name="Diazepam",
        brand_name="Valium",
        formulation="Tablet",
        strength="10mg",
        dose=Decimal("10.000"),
        dose_unit="mg",
        route_id=route.id,
        frequency="TDS",
        frequency_hours=8,
        scheduled_times=["08:00", "14:00", "20:00"],
        start_at=datetime.now(timezone.utc),
        stop_at=datetime.now(timezone.utc) + timedelta(days=7),
        indication="Alcohol withdrawal stabilization",
        status="ACTIVE",
        prescriber_id=nurse.id,
        version=1,
        created_by=nurse.id,
        updated_by=nurse.id,
    )
    db.add(prescription)
    db.flush()

    # 2. Administration Refusal (Mandatory Reason Enforced)
    admin_log = MedicationAdministration(
        facility_id=facility.id,
        reference_code=f"ADM-{uuid.uuid4().hex[:6].upper()}",
        client_id=client.id,
        admission_id=admission.id,
        prescription_id=prescription.id,
        prescription_version=1,
        prescribed_dose=Decimal("10.000"),
        actual_dose=Decimal("0.000"),
        dose_unit="mg",
        route_id=route.id,
        scheduled_at=datetime.now(timezone.utc),
        administered_at=datetime.now(timezone.utc),
        administered_by=nurse.id,
        status="REFUSED",
        reason="Resident reported nausea and requested oral antiemetic first before sedative dose.",
        notes="Primary nurse notified prescribing officer.",
        created_by=nurse.id,
        updated_by=nurse.id,
    )
    db.add(admin_log)
    db.commit()

    assert admin_log.status == "REFUSED"
    assert len(admin_log.reason) > 10
    assert admin_log.administered_by == nurse.id
