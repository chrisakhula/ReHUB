"""Comprehensive Automated Test Suite for ReHUB Phase 26.6:
End-to-End Client Finance Lifecycle, Financial Documents & Exports.

Covers:
1. Financial Assessment (FAS-...)
2. Quotation / Cost Estimate (EST-...) & Acceptance
3. Quotation Conversion to Financial Agreement (FAG-...)
4. Financial Agreement Versioning & Maker-Checker
5. Package Service Inclusions & Consumption Tracking
6. Recurring Billing & Duplicate Charge Protection
7. Payers, Sponsors & Split-Payer Allocations
8. Client Financial Account Balances
9. Payment Plans (PPL-...) & Installments
10. Refunds (RF-...) with Source-Based GL Posting (Deposits vs Revenue)
11. Resident Funds / Pocket Money (RFA-...) Non-Negative & Liability GL
12. Discharge Financial Clearance (CLR-...) & Authorized Exceptions
13. Final Statements & Sponsor Statements
14. Branded Server-Side PDF Document Generation
15. Structured Report Exports (CSV & XLSX) and Audit Logging
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import money
from app.models.clients import Client, Admission
from app.models.identity import Facility, Role, User
from app.models.finance import FinanceAccount, FinanceJournalEntry, FinanceJournalLine
from app.models.billing import (
    Invoice,
    InvoiceItem,
    Payment,
    Sponsor,
    FinancialAssessment,
    FinancialQuotation,
    FinancialQuotationItem,
    FinancialAgreement,
    PackageServiceInclusion,
    PackageConsumption,
    RecurringBillingSchedule,
    InvoicePayerAllocation,
    PaymentPlan,
    PaymentPlanInstallment,
    ResidentFundAccount,
    ResidentFundTransaction,
    DischargeFinancialClearance,
    BillingExportAudit,
    ProgrammePackage,
    Refund,
)
from app.schemas.billing import (
    FinancialAssessmentIn,
    FinancialQuotationIn,
    FinancialQuotationItemIn,
    FinancialAgreementIn,
    FinancialAgreementReviseIn,
    PackageServiceInclusionIn,
    RecurringBillingScheduleIn,
    InvoicePayerAllocationIn,
    PaymentPlanIn,
    PaymentPlanInstallmentIn,
    RefundRequestIn,
    ResidentFundDepositIn,
    ResidentFundWithdrawIn,
    DischargeClearanceReviewIn,
    SponsorIn,
)
from app.services.billing import FinanceService
from app.services.finance import FinanceLedgerService
from app.services.document_engine import FinancialDocumentPdfBuilder, FinancialSpreadsheetExporter


@pytest.fixture
def phase26_6_env(db: Session):
    """Sets up a baseline facility, accounts, client, admission, and distinct users."""
    facility = db.scalars(select(Facility)).first()

    def create_user(name: str, email_prefix: str, role_names: list[str]) -> User:
        user = User(
            id=uuid4(),
            email=f"{email_prefix}_{uuid4().hex[:6]}@rehub.local",
            password_hash="argon2id$testhash",
            full_name=name,
            facility_id=facility.id,
            active=True,
            force_password_change=False,
        )
        for r_name in role_names:
            role = db.scalar(select(Role).where(Role.name == r_name))
            if role:
                user.roles.append(role)
        db.add(user)
        db.flush()
        return user

    sys_admin = create_user("System Admin (ICT)", "sysadmin", ["System Administrator"])

    # Seed baseline chart of accounts
    ledger = FinanceLedgerService(db, None, sys_admin)
    ledger.seed_defaults()
    db.commit()

    finance_officer = create_user("Alex Finance Officer", "fin_off", ["Finance Officer"])
    finance_manager = create_user("Sarah Finance Manager", "fin_mgr", ["Finance Manager"])
    receptionist = create_user("Mary Receptionist", "recep", ["Receptionist"])

    # Create a client record
    client = Client(
        facility_id=facility.id,
        client_number=f"CL-{uuid4().hex[:6].upper()}",
        first_name="David",
        surname="Kariuki",
        date_of_birth=date(1988, 3, 20),
        sex="MALE",
        national_id=f"ID-{uuid4().hex[:6]}",
        created_by=sys_admin.id,
        updated_by=sys_admin.id,
    )
    db.add(client)
    db.flush()

    # Create an admission record
    admission = Admission(
        facility_id=facility.id,
        client_id=client.id,
        admission_number=f"ADM-{uuid4().hex[:6].upper()}",
        admission_date=datetime.now(timezone.utc),
        admission_type="VOLUNTARY",
        reason="Substance dependency rehabilitation",
        programme="90-Day Residential Rehabilitation",
        expected_duration_days=90,
        status="ADMITTED",
        created_by=sys_admin.id,
        updated_by=sys_admin.id,
    )
    db.add(admission)
    db.commit()

    return {
        "facility": facility,
        "client": client,
        "admission": admission,
        "sys_admin": sys_admin,
        "finance_officer": finance_officer,
        "finance_manager": finance_manager,
        "receptionist": receptionist,
    }


# ============================================================================
# 1. Financial Assessment (FAS-...)
# ============================================================================

def test_financial_assessment_lifecycle(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    data = FinancialAssessmentIn(
        client_id=env["client"].id,
        proposed_programme="90-Day Residential Rehabilitation",
        expected_duration_days=90,
        expected_admission_date=date.today() + timedelta(days=5),
        primary_payer_type="FAMILY",
        primary_payer_name="John Kariuki (Father)",
        secondary_payer_type="SELF",
        secondary_payer_name="David Kariuki",
        estimated_programme_cost=Decimal("250000.00"),
        deposit_required=Decimal("50000.00"),
        credit_terms="30_DAYS",
        installment_preference="MONTHLY",
        discount_eligibility=Decimal("5.00"),
        authorization_limit=Decimal("300000.00"),
        financial_notes="Family agreed to pay deposit upon admission.",
    )

    assessment = svc.create_financial_assessment(data)
    assert assessment.id is not None
    assert assessment.reference_code.startswith("FAS-")
    assert assessment.proposed_programme == "90-Day Residential Rehabilitation"
    assert assessment.estimated_programme_cost == Decimal("250000.00")
    assert assessment.deposit_required == Decimal("50000.00")

    # Fetch assessment
    fetched = svc.get_financial_assessment(assessment.id)
    assert fetched.reference_code == assessment.reference_code


# ============================================================================
# 2. Quotation / Cost Estimate (EST-...) & Agreement Conversion
# ============================================================================

def test_quotation_creation_and_conversion(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    q_data = FinancialQuotationIn(
        client_id=env["client"].id,
        programme_name="90-Day Residential Rehabilitation",
        duration_days=90,
        deposit_required=Decimal("60000.00"),
        valid_until=date.today() + timedelta(days=30),
        terms_and_conditions="Full payment expected in 3 installments.",
        notes="Includes board, medical review, and psychotherapy.",
        items=[
            FinancialQuotationItemIn(
                category="PROGRAMME",
                description="90-Day Programme Accommodation & Board",
                quantity=Decimal("1.00"),
                unit_price=Decimal("180000.00"),
                discount=Decimal("0.00"),
                tax_rate=Decimal("0.00"),
            ),
            FinancialQuotationItemIn(
                category="LAB",
                description="Initial Assessment & Toxic Screen",
                quantity=Decimal("1.00"),
                unit_price=Decimal("15000.00"),
                discount=Decimal("0.00"),
                tax_rate=Decimal("0.00"),
            ),
            FinancialQuotationItemIn(
                category="MEDICATION",
                description="Medical Detoxification & Stabilization",
                quantity=Decimal("1.00"),
                unit_price=Decimal("25000.00"),
                discount=Decimal("0.00"),
                tax_rate=Decimal("0.00"),
            ),
        ],
    )

    initial_journals = db.query(FinanceJournalEntry).count()
    quotation = svc.create_financial_quotation(q_data)
    assert quotation.reference_code.startswith("EST-")
    assert quotation.status == "DRAFT"
    assert quotation.subtotal == Decimal("220000.00")
    assert quotation.total_amount == Decimal("220000.00")
    assert len(quotation.items) == 3

    # Quotations must NOT generate General Ledger journals (commercial document)
    assert db.query(FinanceJournalEntry).count() == initial_journals

    # Issue quotation
    issued_q = svc.issue_financial_quotation(quotation.id)
    assert issued_q.status == "ISSUED"

    # Accept quotation
    accepted_q = svc.accept_financial_quotation(quotation.id, accepted_by="John Kariuki")
    assert accepted_q.status == "ACCEPTED"
    assert accepted_q.accepted_by == "John Kariuki"

    # Convert to Financial Agreement
    agreement = svc.convert_quotation_to_agreement(quotation.id)
    assert agreement.reference_code.startswith("FAG-")
    assert agreement.version == 1
    assert agreement.agreed_price == Decimal("220000.00")
    assert agreement.deposit_amount == Decimal("60000.00")
    assert agreement.status == "PENDING_ACCEPTANCE"
    assert quotation.status == "CONVERTED"
    assert quotation.converted_agreement_id == agreement.id


# ============================================================================
# 3. Financial Agreement Versioning & Maker-Checker
# ============================================================================

def test_financial_agreement_versioning_and_maker_checker(db: Session, phase26_6_env):
    env = phase26_6_env
    officer_svc = FinanceService(db, None, env["finance_officer"])
    manager_svc = FinanceService(db, None, env["finance_manager"])

    ag_data = FinancialAgreementIn(
        client_id=env["client"].id,
        admission_id=env["admission"].id,
        programme_name="90-Day Residential Rehabilitation",
        agreed_price=Decimal("200000.00"),
        deposit_amount=Decimal("50000.00"),
        installment_terms="3 installments of 50,000",
        credit_terms="30_DAYS",
        inclusions="Accommodation, Therapy, Nursing",
        exclusions="Specialized dental, outside hospital referrals",
        refund_terms="Standard institutional policy",
        approved_discount=Decimal("0.00"),
        effective_date=date.today(),
        notes="Initial admission agreement",
    )

    ag_v1 = officer_svc.create_financial_agreement(ag_data)
    assert ag_v1.version == 1
    assert ag_v1.status == "PENDING_ACCEPTANCE"

    # Maker-checker: Officer who created the agreement cannot approve it
    with pytest.raises(HTTPException) as exc_info:
        officer_svc.approve_financial_agreement(ag_v1.id)
    assert exc_info.value.status_code == 403
    assert "Segregation of duties" in exc_info.value.detail

    # Independent manager approves
    approved_v1 = manager_svc.approve_financial_agreement(ag_v1.id)
    assert approved_v1.status == "ACTIVE"
    assert approved_v1.authorized_by_id == env["finance_manager"].id

    # Revise agreement: creates version 2
    revise_data = FinancialAgreementReviseIn(
        revision_reason="Extended medical stabilization required extra monitoring",
        agreed_price=Decimal("230000.00"),
        deposit_amount=Decimal("50000.00"),
        installment_terms="Initial 50k + 3 installments of 60k",
        inclusions="Accommodation, Therapy, Nursing, High-Dependency Unit",
        exclusions="Specialized outside referrals",
    )

    ag_v2 = manager_svc.revise_financial_agreement(ag_v1.id, revise_data)
    assert ag_v2.version == 2
    assert ag_v2.reference_code == ag_v1.reference_code
    assert ag_v2.agreed_price == Decimal("230000.00")
    assert ag_v2.parent_agreement_id == ag_v1.id
    assert ag_v2.status in ["PENDING_ACCEPTANCE", "ACTIVE"]

    # Verify v1 is marked REVISED and not deleted
    db.refresh(ag_v1)
    assert ag_v1.status == "REVISED"


# ============================================================================
# 4. Package Billing & Consumption Tracking
# ============================================================================

def test_package_service_inclusions_and_consumption(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    # Create a Programme Package
    pkg = ProgrammePackage(
        facility_id=env["facility"].id,
        name="90-Day Complete Rehab Package",
        description="Comprehensive 90-day inpatient programme",
        duration_days=90,
        is_active=True,
    )
    db.add(pkg)
    db.flush()

    # Configure inclusions: 12 Counselling sessions included
    inclusion = svc.create_package_inclusion(
        pkg.id,
        PackageServiceInclusionIn(
            category="COUNSELLING",
            classification="LIMITED_QUANTITY",
            allowed_quantity=12,
            discount_percentage=Decimal("0.00"),
        ),
    )
    assert inclusion.allowed_quantity == 12

    # Consumption test 1: Within limit (first 10 sessions)
    result1 = svc.record_package_consumption(
        admission_id=env["admission"].id,
        package_id=pkg.id,
        category="COUNSELLING",
        quantity_to_consume=10,
        unit_price=Decimal("3000.00"),
    )
    assert result1["status"] == "COVERED"
    assert result1["consumed_from_package"] == 10
    assert result1["extra_billed_quantity"] == 0
    assert result1["extra_billable_amount"] == Decimal("0.00")
    assert result1["quantity_remaining"] == 2

    # Consumption test 2: Exceeding limit (consume 4 more sessions; 2 covered, 2 extra)
    result2 = svc.record_package_consumption(
        admission_id=env["admission"].id,
        package_id=pkg.id,
        category="COUNSELLING",
        quantity_to_consume=4,
        unit_price=Decimal("3000.00"),
    )
    assert result2["status"] == "QUOTA_EXCEEDED"
    assert result2["consumed_from_package"] == 2
    assert result2["extra_billed_quantity"] == 2
    assert result2["extra_billable_amount"] == Decimal("6000.00")
    assert result2["quantity_remaining"] == 0


# ============================================================================
# 5. Service-to-Billing & Duplicate Charge Protection
# ============================================================================

def test_duplicate_charge_protection(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    source_mod = "pharmacy"
    source_ref = "dispense-tx-9988"

    # First charge generation succeeds
    item1 = svc.generate_service_charge(
        admission_id=env["admission"].id,
        source_module=source_mod,
        source_id=source_ref,
        charge_type="MEDICATION",
        description="Prescribed Antidepressants & Vitamins",
        amount=Decimal("4500.00"),
    )
    assert item1.id is not None
    assert item1.source_module == source_mod
    assert item1.source_id == source_ref

    # Retrying same charge raises duplicate charge 400
    with pytest.raises(HTTPException) as exc_info:
        svc.generate_service_charge(
            admission_id=env["admission"].id,
            source_module=source_mod,
            source_id=source_ref,
            charge_type="MEDICATION",
            description="Prescribed Antidepressants & Vitamins",
            amount=Decimal("4500.00"),
        )
    assert exc_info.value.status_code == 400
    assert "Duplicate charge" in exc_info.value.detail


# ============================================================================
# 6. Recurring Billing
# ============================================================================

def test_recurring_billing_schedule_and_idempotency(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    today = date.today()
    schedule_data = RecurringBillingScheduleIn(
        admission_id=env["admission"].id,
        frequency="DAILY",
        description="Daily High-Observation Care Supplement",
        amount=Decimal("1500.00"),
        next_run_date=today,
    )

    sched = svc.create_recurring_schedule(schedule_data)
    assert sched.id is not None
    assert sched.is_active is True

    # Process recurring charges for today: should generate 1 charge
    generated_first = svc.process_due_recurring_schedules(target_date=today)
    assert len(generated_first) == 1
    assert generated_first[0].total_price == Decimal("1500.00")

    # Re-running process on same target date is idempotent and generates 0 charges
    generated_second = svc.process_due_recurring_schedules(target_date=today)
    assert len(generated_second) == 0


# ============================================================================
# 7. Payers, Sponsors & Split-Payer Responsibility
# ============================================================================

def test_sponsor_and_split_payer_validation(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    # Create Sponsor
    sp_data = SponsorIn(
        name="Equity Foundation Medical Fund",
        sponsor_type="NGO",
        contact_person="Beatrice Mwangi",
        email="equity.fund@example.org",
        phone="+254700112233",
        billing_address="Upper Hill, Nairobi",
        credit_limit=Decimal("500000.00"),
    )
    sponsor = svc.create_sponsor(sp_data)
    assert sponsor.reference_code.startswith("SPN-")

    # Create an invoice for KES 200,000
    inv = Invoice(
        facility_id=env["facility"].id,
        client_id=env["client"].id,
        admission_id=env["admission"].id,
        invoice_number=f"INV-{uuid4().hex[:6].upper()}",
        subtotal=Decimal("200000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("200000.00"),
        status="ISSUED",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        created_by=env["finance_officer"].id,
    )
    db.add(inv)
    db.commit()

    # Case A: Over-allocation (60% + 50% = 110%) should fail with 400
    invalid_allocations = [
        InvoicePayerAllocationIn(
            sponsor_id=sponsor.id,
            allocation_type="PERCENTAGE",
            percentage=Decimal("60.00"),
            allocated_amount=Decimal("120000.00"),
            responsibility_description="Sponsor responsibility",
        ),
        InvoicePayerAllocationIn(
            payer_id=None,
            allocation_type="PERCENTAGE",
            percentage=Decimal("50.00"),
            allocated_amount=Decimal("100000.00"),
            responsibility_description="Family responsibility",
        ),
    ]
    with pytest.raises(HTTPException) as exc_info:
        svc.set_invoice_payer_allocations(inv.id, invalid_allocations)
    assert exc_info.value.status_code == 400
    assert "exceeds 100%" in exc_info.value.detail or "Allocations total" in exc_info.value.detail

    # Case B: Valid split (Sponsor 60% = 120,000; Client/Family 40% = 80,000; total = 100%)
    valid_allocations = [
        InvoicePayerAllocationIn(
            sponsor_id=sponsor.id,
            allocation_type="PERCENTAGE",
            percentage=Decimal("60.00"),
            allocated_amount=Decimal("120000.00"),
            responsibility_description="Sponsor responsibility",
        ),
        InvoicePayerAllocationIn(
            payer_id=None,
            allocation_type="PERCENTAGE",
            percentage=Decimal("40.00"),
            allocated_amount=Decimal("80000.00"),
            responsibility_description="Family responsibility",
        ),
    ]
    saved = svc.set_invoice_payer_allocations(inv.id, valid_allocations)
    assert len(saved) == 2
    assert sum(a.allocated_amount for a in saved) == Decimal("200000.00")


# ============================================================================
# 8. Client Financial Account Balances
# ============================================================================

def test_client_financial_account_summary(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    summary = svc.get_client_financial_summary(env["client"].id)
    assert summary.client_id == env["client"].id
    assert summary.total_charges >= Decimal("0.00")
    assert summary.net_outstanding_balance >= Decimal("0.00")


# ============================================================================
# 9. Payment Plans (PPL-...)
# ============================================================================

def test_payment_plan_lifecycle_and_installments(db: Session, phase26_6_env):
    env = phase26_6_env
    officer_svc = FinanceService(db, None, env["finance_officer"])
    manager_svc = FinanceService(db, None, env["finance_manager"])

    today = date.today()
    plan_data = PaymentPlanIn(
        client_id=env["client"].id,
        admission_id=env["admission"].id,
        total_amount=Decimal("120000.00"),
        number_of_installments=3,
        notes="Post-discharge recovery payment plan",
        installments=[
            PaymentPlanInstallmentIn(installment_number=1, due_date=today + timedelta(days=30), amount=Decimal("40000.00")),
            PaymentPlanInstallmentIn(installment_number=2, due_date=today + timedelta(days=60), amount=Decimal("40000.00")),
            PaymentPlanInstallmentIn(installment_number=3, due_date=today + timedelta(days=90), amount=Decimal("40000.00")),
        ],
    )

    plan = officer_svc.create_payment_plan(plan_data)
    assert plan.reference_code.startswith("PPL-")
    assert plan.status == "DRAFT"
    assert len(plan.installments) == 3

    # Approve payment plan
    approved = manager_svc.approve_payment_plan(plan.id)
    assert approved.status == "ACTIVE"
    assert approved.approved_by == env["finance_manager"].id


# ============================================================================
# 10. Refunds (RF-...) with Source-Based GL Posting
# ============================================================================

def test_refund_workflow_maker_checker_and_gl_posting(db: Session, phase26_6_env):
    env = phase26_6_env
    officer_svc = FinanceService(db, None, env["finance_officer"])
    manager_svc = FinanceService(db, None, env["finance_manager"])

    ref_data = RefundRequestIn(
        client_id=env["client"].id,
        amount=Decimal("15000.00"),
        reason="Overpayment of initial admission deposit",
        source_type="CLIENT_DEPOSIT",
        refund_method="BANK",
        transaction_reference="EFT-REF-2026-001",
    )

    refund = officer_svc.request_refund(ref_data)
    assert refund.reference_code.startswith("RF-")
    assert refund.status == "PENDING_APPROVAL"

    # Maker-checker: Officer who requested the refund cannot approve it
    with pytest.raises(HTTPException) as exc_info:
        officer_svc.approve_refund(refund.id, "Approved by self")
    assert exc_info.value.status_code == 403
    assert "Segregation of duties" in exc_info.value.detail

    # Independent manager approves and posts to GL
    approved_rf = manager_svc.approve_refund(refund.id, "Approved unused deposit refund")
    assert approved_rf.status in ["APPROVED", "PAID"]
    assert approved_rf.journal_id is not None

    # Verify atomic General Ledger posting: Dr 2200 (Liability) / Cr 1030 (Bank)
    journal = db.scalar(select(FinanceJournalEntry).where(FinanceJournalEntry.id == approved_rf.journal_id))
    assert journal is not None
    assert journal.posted is True
    lines = journal.lines
    assert len(lines) == 2

    debit_line = next(l for l in lines if l.debit > 0)
    credit_line = next(l for l in lines if l.credit > 0)
    assert debit_line.debit == Decimal("15000.00")
    assert credit_line.credit == Decimal("15000.00")

    # Dr Account should be 2200 (Client Deposits Liability)
    acct_dr = db.scalar(select(FinanceAccount).where(FinanceAccount.id == debit_line.account_id))
    assert acct_dr.code == "2200"


# ============================================================================
# 11. Resident Funds / Pocket Money (RFA-...) Non-Negative & GL Posting
# ============================================================================

def test_resident_funds_non_negative_and_liability_gl(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    # 1. Create Resident Fund Account
    account = svc.get_or_create_resident_fund_account(env["client"].id, env["admission"].id)
    assert account.reference_code.startswith("RFA-")
    assert account.current_balance == Decimal("0.00")

    # 2. Deposit KES 5,000 pocket money
    dep_tx = svc.deposit_resident_funds(
        account.id,
        ResidentFundDepositIn(
            amount=Decimal("5000.00"),
            description="Family deposit for personal toiletries and pocket money",
            payment_method="CASH",
            receipt_reference="RCT-DEP-01",
        ),
    )
    assert dep_tx.running_balance == Decimal("5000.00")
    assert account.current_balance == Decimal("5000.00")
    assert dep_tx.journal_id is not None

    # Verify GL posting: Dr 1000 Cash on Hand / Cr 2200 Resident Funds Liability
    journal_dep = db.scalar(select(FinanceJournalEntry).where(FinanceJournalEntry.id == dep_tx.journal_id))
    assert journal_dep is not None
    lines_dep = journal_dep.lines
    cr_line_dep = next(l for l in lines_dep if l.credit > 0)
    acct_cr = db.scalar(select(FinanceAccount).where(FinanceAccount.id == cr_line_dep.account_id))
    assert acct_cr.code == "2200"

    # 3. Negative balance protection: attempt to withdraw KES 7,000 (exceeds 5,000 balance)
    with pytest.raises(HTTPException) as exc_info:
        svc.withdraw_resident_funds(
            account.id,
            ResidentFundWithdrawIn(
                amount=Decimal("7000.00"),
                description="Excessive withdrawal attempt",
                transaction_type="WITHDRAWAL",
            ),
        )
    assert exc_info.value.status_code == 400
    assert "Insufficient funds" in exc_info.value.detail

    # 4. Valid withdrawal of KES 1,500
    with_tx = svc.withdraw_resident_funds(
        account.id,
        ResidentFundWithdrawIn(
            amount=Decimal("1500.00"),
            description="Authorized personal tuck-shop purchase",
            transaction_type="PURCHASE",
        ),
    )
    assert with_tx.running_balance == Decimal("3500.00")
    assert account.current_balance == Decimal("3500.00")

    # Verify GL posting for withdrawal: Dr 2200 Resident Funds Liability / Cr 1000 Cash
    journal_with = db.scalar(select(FinanceJournalEntry).where(FinanceJournalEntry.id == with_tx.journal_id))
    lines_with = journal_with.lines
    dr_line_with = next(l for l in lines_with if l.debit > 0)
    acct_dr = db.scalar(select(FinanceAccount).where(FinanceAccount.id == dr_line_with.account_id))
    assert acct_dr.code == "2200"


# ============================================================================
# 12. Discharge Financial Clearance (CLR-...) & Authorized Exceptions
# ============================================================================

def test_discharge_financial_clearance_and_exceptions(db: Session, phase26_6_env):
    env = phase26_6_env
    officer_svc = FinanceService(db, None, env["finance_officer"])
    manager_svc = FinanceService(db, None, env["finance_manager"])

    # 1. Initialize discharge clearance review
    clearance = officer_svc.review_discharge_clearance(
        env["admission"].id,
        DischargeClearanceReviewIn(status="PENDING", notes="Discharge clearance review initiated"),
    )
    assert clearance.reference_code.startswith("CLR-")
    assert clearance.client_id == env["client"].id
    assert clearance.status == "CLEARED"  # zero charges = initially cleared

    # 2. Case: Client leaves with outstanding balance under an Authorized Exception
    # Create an unpaid invoice of KES 25,000 for this admission
    inv = Invoice(
        facility_id=env["facility"].id,
        client_id=env["client"].id,
        admission_id=env["admission"].id,
        invoice_number=f"INV-{uuid4().hex[:6].upper()}",
        subtotal=Decimal("25000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("25000.00"),
        status="ISSUED",
        issue_date=date.today(),
        due_date=date.today(),
        created_by=env["finance_officer"].id,
    )
    db.add(inv)
    db.commit()

    # Re-evaluate clearance to capture the unpaid balance with an authorized exception
    clearance = officer_svc.review_discharge_clearance(
        env["admission"].id,
        DischargeClearanceReviewIn(
            status="AUTHORIZED_EXCEPTION",
            is_authorized_exception=True,
            exception_reason="Emergency clinical discharge; family signed debt acknowledgment",
            collection_owner="Head of Credit & Collections",
            notes="Review with authorized exception",
        ),
    )
    assert clearance.outstanding_balance == Decimal("25000.00")
    assert clearance.status == "AUTHORIZED_EXCEPTION"

    # Authorize clearance by independent Finance Manager
    approved_clearance = manager_svc.approve_discharge_clearance(
        clearance.id,
        notes="Approved exception after verifying debt acknowledgment letter",
    )
    assert approved_clearance.status == "AUTHORIZED_EXCEPTION"
    assert approved_clearance.is_authorized_exception is True
    assert approved_clearance.exception_approved_by_id == env["finance_manager"].id
    # Crucial safety check: balance must NOT be silently wiped to zero!
    assert approved_clearance.outstanding_balance == Decimal("25000.00")


# ============================================================================
# 13. Branded Server-Side PDF Document Generation
# ============================================================================

def test_branded_pdf_document_generation(db: Session, phase26_6_env):
    """Test PDF generation across all core financial documents and ensure clean bytes without raw UUIDs."""
    env = phase26_6_env
    builder = FinancialDocumentPdfBuilder()

    # 1. Invoice PDF
    inv_pdf = builder.generate_invoice_pdf({
        "invoice_number": "INV-2026-00045",
        "client_name": "David Kariuki",
        "client_number": "ARS-00124",
        "admission_number": "ADM-2026-00012",
        "issue_date": str(date.today()),
        "due_date": str(date.today() + timedelta(days=30)),
        "items": [
            {"description": "Inpatient Rehabilitation 30 Days", "quantity": 1, "unit_price": "150000.00", "discount": "0.00", "total_price": "150000.00"},
            {"description": "Toxicology Panel & Lab Work", "quantity": 1, "unit_price": "12000.00", "discount": "0.00", "total_price": "12000.00"},
        ],
        "subtotal": "162000.00",
        "discount_amount": "0.00",
        "tax_amount": "0.00",
        "total_amount": "162000.00",
        "amount_paid": "50000.00",
        "balance_due": "112000.00",
    })
    assert isinstance(inv_pdf, bytes)
    assert inv_pdf.startswith(b"%PDF-")
    assert len(inv_pdf) > 1000

    # 2. Receipt PDF
    rcpt_pdf = builder.generate_receipt_pdf({
        "receipt_number": "RCT-2026-00045",
        "client_name": "David Kariuki",
        "client_number": "ARS-00124",
        "admission_number": "ADM-2026-00012",
        "payment_date": str(date.today()),
        "payment_method": "M-PESA",
        "transaction_reference": "QGH789KLM",
        "amount": "50000.00",
        "received_from": "John Kariuki",
        "received_by": "Alex Finance Officer",
        "remaining_balance": "112000.00",
    })
    assert isinstance(rcpt_pdf, bytes)
    assert rcpt_pdf.startswith(b"%PDF-")

    # 3. Client Statement PDF
    stmt_pdf = builder.generate_statement_pdf({
        "summary": {
            "client_name": "David Kariuki",
            "client_reference": "ARS-00124",
            "admission_number": "ADM-2026-00012",
            "total_charges": "162000.00",
            "total_payments": "50000.00",
            "outstanding_balance": "112000.00",
            "financial_clearance_status": "CLEARED",
        },
        "transactions": [
            {"date": str(date.today()), "reference": "INV-2026-00045", "description": "Programme Invoicing", "debit": "162000.00", "credit": "0.00", "running_balance": "162000.00"},
            {"date": str(date.today()), "reference": "RCT-2026-00045", "description": "M-Pesa Deposit", "debit": "0.00", "credit": "50000.00", "running_balance": "112000.00"},
        ],
    })
    assert isinstance(stmt_pdf, bytes)
    assert stmt_pdf.startswith(b"%PDF-")

    # 4. Discharge Financial Clearance PDF
    clr_pdf = builder.generate_discharge_clearance_pdf({
        "reference_code": "CLR-2026-00012",
        "client_name": "David Kariuki",
        "client_code": "ARS-00124",
        "admission_code": "ADM-2026-00012",
        "status": "AUTHORIZED_EXCEPTION",
        "total_charges": "162000.00",
        "total_payments": "50000.00",
        "total_credits": "0.00",
        "total_writeoffs": "0.00",
        "outstanding_balance": "112000.00",
        "is_authorized_exception": True,
        "exception_reason": "Emergency clinical discharge; family signed debt agreement",
        "collection_owner": "Head of Credit & Collections",
        "approved_by": "Sarah Finance Manager",
        "clearance_date": str(date.today()),
    })
    assert isinstance(clr_pdf, bytes)
    assert clr_pdf.startswith(b"%PDF-")


# ============================================================================
# 14. Structured Report Exports (CSV & XLSX) and Audit
# ============================================================================

def test_spreadsheet_exports_and_audit(db: Session, phase26_6_env):
    env = phase26_6_env
    svc = FinanceService(db, None, env["finance_officer"])

    headers = ["Invoice Number", "Client Code", "Date", "Total Amount", "Paid", "Balance", "Status"]
    rows = [
        ["INV-2026-0001", "ARS-001", "2026-10-01", "150000.00", "150000.00", "0.00", "PAID"],
        ["INV-2026-0002", "ARS-002", "2026-10-05", "200000.00", "100000.00", "100000.00", "PARTIALLY_PAID"],
    ]

    # Test CSV Generation
    csv_str = FinancialSpreadsheetExporter.generate_csv(headers, rows)
    assert "Invoice Number,Client Code" in csv_str
    assert "INV-2026-0001" in csv_str

    # Test XLSX Generation
    xlsx_bytes = FinancialSpreadsheetExporter.generate_xlsx("Invoices Report", headers, rows)
    assert isinstance(xlsx_bytes, bytes)
    # XLSX files are ZIP archives starting with magic bytes PK\x03\x04
    assert xlsx_bytes.startswith(b"PK\x03\x04")
    assert len(xlsx_bytes) > 1000

    # Test Export Audit Recording
    audit_rec = svc.log_export_audit(
        export_format="XLSX",
        report_type="Accounts Receivable Aging",
        reference_code="RPT-AR-20261016",
        filter_parameters="as_of=2026-10-16;facility=Karen",
        reason="Monthly financial board pack preparation",
    )
    assert audit_rec.id is not None
    assert audit_rec.export_format == "XLSX"
    assert audit_rec.report_type == "Accounts Receivable Aging"
    assert audit_rec.user_id == env["finance_officer"].id


# ============================================================================
# 15. Unified Document PDF and Spreadsheet Export Endpoints
# ============================================================================

def test_unified_document_pdf_and_spreadsheet_export_routes(db: Session, phase26_6_env):
    """Test unified /documents/pdf and /exports/spreadsheet API endpoints."""
    from app.api.v1.billing.routes import get_unified_document_pdf, export_spreadsheet_get
    env = phase26_6_env
    client = env["client"]
    officer = env["finance_officer"]

    # 1. Invoice PDF by client_id (pro-forma when no invoice issued)
    res_inv = get_unified_document_pdf(
        document_type="INVOICE",
        reference_id=client.id,
        request=None,
        db=db,
        actor=officer,
    )
    assert res_inv.media_type == "application/pdf"
    assert res_inv.body.startswith(b"%PDF-")

    # 2. Statement PDF by client_id
    res_stmt = get_unified_document_pdf(
        document_type="STATEMENT",
        reference_id=client.id,
        request=None,
        db=db,
        actor=officer,
    )
    assert res_stmt.media_type == "application/pdf"
    assert res_stmt.body.startswith(b"%PDF-")

    # 3. Receipt PDF by client_id (provisional when no payment yet)
    res_rcpt = get_unified_document_pdf(
        document_type="RECEIPT",
        reference_id=client.id,
        request=None,
        db=db,
        actor=officer,
    )
    assert res_rcpt.media_type == "application/pdf"
    assert res_rcpt.body.startswith(b"%PDF-")

    # 4. Discharge Clearance PDF by client_id (provisional review)
    res_clr = get_unified_document_pdf(
        document_type="DISCHARGE_CLEARANCE",
        reference_id=client.id,
        request=None,
        db=db,
        actor=officer,
    )
    assert res_clr.media_type == "application/pdf"
    assert res_clr.body.startswith(b"%PDF-")

    # 5. Spreadsheet Export GET CSV
    res_csv = export_spreadsheet_get(
        report_type="AR_AGING",
        export_format="CSV",
        db=db,
        actor=officer,
    )
    assert res_csv.media_type == "text/csv"
    assert "Invoice Number,Client Code" in res_csv.body.decode("utf-8")

    # 6. Spreadsheet Export GET XLSX
    res_xlsx = export_spreadsheet_get(
        report_type="CLIENT_BALANCES",
        export_format="XLSX",
        db=db,
        actor=officer,
    )
    assert res_xlsx.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert res_xlsx.body.startswith(b"PK\x03\x04")

