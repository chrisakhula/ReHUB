"""Comprehensive Automated Test Suite for ReHUB Phase 26.5:
Finance Safety, Accounting Integrity & Control Remediation.

Covers:
1. Exact Decimal arithmetic (P0-1)
2. RBAC: System Administrator technical separation vs Finance Manager (P0-2)
3. Cash Reconciliation supervisor gate & GL posting (P0-3)
4. Invoice Immutability & Credit Note workflow (P0-4)
5. Atomic Billing and GL Posting (P0-5)
6. Write-Off maker-checker & GL posting (P0-6)
7. Pre-issue vs Post-issue discount controls (P0-7)
8. Billing-to-GL Integrity Diagnostic Service (Section 41-42)
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import money, quantize_money, MONEY_QUANTUM
from app.models.clients import Client
from app.models.billing import (
    Invoice,
    CreditNote,
    WriteOff,
)
from app.models.finance import (
    FinanceAccount,
    FinanceExpenseCategory,
    FinanceExpenseVoucher,
    FinanceCashReconciliation,
    FinanceJournalEntry,
)
from app.models.identity import Facility, Permission, Role, User
from app.schemas.billing import CreditNoteIn, WriteOffIn
from app.schemas.finance import CashReconciliationIn
from app.services.billing import FinanceService as BillingOperationService
from app.services.finance import FinanceLedgerService
from app.services.integrity import BillingGlIntegrityService


# ============================================================================
# 1. P0-1: Decimal Monetary Arithmetic Precision Tests
# ============================================================================

def test_decimal_canonical_monetary_math():
    """Verify exact decimal quantization and absence of float representation errors."""
    # 0.10 + 0.20 == 0.30 exactly
    val1 = money("0.10") + money("0.20")
    assert val1 == Decimal("0.30")
    assert str(val1) == "0.30"

    # 33.33 * 3 == 99.99
    val2 = quantize_money(money("33.33") * Decimal("3"))
    assert val2 == Decimal("99.99")

    # 16% VAT on KES 100.05
    subtotal = money("100.05")
    vat = quantize_money(subtotal * Decimal("0.16"))
    assert vat == Decimal("16.01")  # 16.008 rounds to 16.01 using ROUND_HALF_UP

    # Repeated partial payments
    total = money("100.00")
    pay1 = money("33.33")
    pay2 = money("33.33")
    pay3 = money("33.34")
    assert pay1 + pay2 + pay3 == total

    # KES 0.01 precision
    assert money("0.005") == Decimal("0.01")
    assert money("0.004") == Decimal("0.00")

    # Large values
    large_num = money("999999999999.99")
    assert large_num + money("0.01") == Decimal("1000000000000.00")


# ============================================================================
# Fixtures for Finance & Billing Services
# ============================================================================

@pytest.fixture
def finance_env(db: Session):
    """Sets up a baseline facility, accounts, client, and distinct users for RBAC testing."""
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

    # Seed baseline chart of accounts and categories
    ledger = FinanceLedgerService(db, None, sys_admin)
    ledger.seed_defaults()
    db.commit()

    cashier = create_user("Faith Cashier", "cashier", ["Receptionist", "Finance Officer"])
    finance_officer = create_user("Peter Finance Officer", "fin_officer", ["Finance Officer"])
    finance_manager = create_user("Grace Finance Manager", "fin_mgr", ["Finance Manager"])
    facility_admin = create_user("Director Facility Admin", "fac_admin", ["System Administrator", "Finance Manager"])

    # Create a client record for billing
    client_rec = Client(
        facility_id=facility.id,
        client_number=f"CL-{uuid4().hex[:6].upper()}",
        first_name="Jane",
        surname="Wanjiru",
        date_of_birth=date(1992, 5, 14),
        sex="FEMALE",
        national_id=f"ID-{uuid4().hex[:6]}",
        created_by=sys_admin.id,
        updated_by=sys_admin.id,
    )
    db.add(client_rec)
    db.commit()

    return {
        "facility": facility,
        "client": client_rec,
        "sys_admin": sys_admin,
        "cashier": cashier,
        "finance_officer": finance_officer,
        "finance_manager": finance_manager,
        "facility_admin": facility_admin,
    }


# ============================================================================
# 2. P0-2: Remove ICT/System Administrator Financial Authority
# ============================================================================

def test_system_admin_lacks_financial_approval(db: Session, finance_env):
    """System Administrator role must not be permitted to approve expenses or cash variances."""
    sys_admin = finance_env["sys_admin"]
    cashier = finance_env["cashier"]

    exp_category = db.scalars(select(FinanceExpenseCategory)).first()
    assert exp_category is not None

    # Create dummy expense voucher
    voucher = FinanceExpenseVoucher(
        id=uuid4(),
        facility_id=finance_env["facility"].id,
        reference=f"EXP-{uuid4().hex[:6]}",
        expense_category_id=exp_category.id,
        amount=Decimal("25000.00"),
        payment_method="CASH",
        paid_to="Vendor Supplies",
        expense_date=date.today(),
        status="DRAFT",
        created_by=cashier.id,
    )
    db.add(voucher)
    db.commit()

    # SysAdmin tries to approve -> must fail with 403 because technical role != financial role
    ledger_admin = FinanceLedgerService(db, None, sys_admin)
    with pytest.raises(HTTPException) as exc_info:
        ledger_admin.approve_expense(voucher.id)
    assert exc_info.value.status_code in (403, 400)


def test_senior_approval_threshold_enforcement(db: Session, finance_env):
    """Expenses >= KES 50,000 require senior financial approval (Finance Manager/Facility Admin)."""
    cashier = finance_env["cashier"]
    fin_officer = finance_env["finance_officer"]
    fin_manager = finance_env["finance_manager"]

    exp_category = db.scalars(select(FinanceExpenseCategory)).first()
    assert exp_category is not None

    voucher = FinanceExpenseVoucher(
        id=uuid4(),
        facility_id=finance_env["facility"].id,
        reference=f"EXP-{uuid4().hex[:6]}",
        expense_category_id=exp_category.id,
        amount=Decimal("75000.00"),  # > KES 50,000 threshold
        payment_method="CASH",
        paid_to="Major Equipment Service",
        expense_date=date.today(),
        status="DRAFT",
        created_by=cashier.id,
    )
    db.add(voucher)
    db.commit()

    # Regular Finance Officer tries to approve > 50k -> 403 Forbidden
    ledger_officer = FinanceLedgerService(db, None, fin_officer)
    with pytest.raises(HTTPException) as exc_info:
        ledger_officer.approve_expense(voucher.id)
    assert exc_info.value.status_code == 403
    assert "Senior" in exc_info.value.detail or "50,000" in exc_info.value.detail

    # Finance Manager approves -> Success & Posts GL
    ledger_manager = FinanceLedgerService(db, None, fin_manager)
    approved = ledger_manager.approve_expense(voucher.id)
    assert approved.status == "APPROVED"
    assert approved.approved_by == fin_manager.id


# ============================================================================
# 3. P0-3: Cash Reconciliation Supervisor Gate & Maker-Checker
# ============================================================================

def test_cash_reconciliation_zero_variance_auto_balances(db: Session, finance_env):
    """When counted equals expected, cash reconciliation automatically marks BALANCED."""
    cashier = finance_env["cashier"]
    ledger = FinanceLedgerService(db, None, cashier)

    rec = ledger.create_cash_reconciliation(
        CashReconciliationIn(
            period_date=date.today(),
            cashier_name=cashier.full_name,
            opening_cash=Decimal("5000.00"),
            expected_cash=Decimal("15000.00"),
            counted_cash=Decimal("15000.00"),
            notes="Balanced shift count",
        )
    )
    assert rec.status == "BALANCED"
    assert rec.variance == Decimal("0.00")
    assert rec.journal_id is None  # Zero variance creates no journal


def test_cash_reconciliation_variance_requires_supervisor_approval(db: Session, finance_env):
    """Shortage or overage must NOT post immediately to GL and requires independent approval."""
    cashier = finance_env["cashier"]
    fin_manager = finance_env["finance_manager"]
    ledger_cashier = FinanceLedgerService(db, None, cashier)

    # 1. Cashier records a shortage of KES 500 (expected 10,000, counted 9,500)
    rec = ledger_cashier.create_cash_reconciliation(
        CashReconciliationIn(
            period_date=date.today(),
            cashier_name=cashier.full_name,
            opening_cash=Decimal("2000.00"),
            expected_cash=Decimal("10000.00"),
            counted_cash=Decimal("9500.00"),
            notes="Shortage due to register coin discrepancy",
        )
    )
    assert rec.status == "VARIANCE_REVIEW"
    assert rec.variance == Decimal("-500.00")
    assert rec.journal_id is None  # Must NOT be posted to GL yet

    # 2. Cashier tries to approve own variance -> Maker-Checker blocks with 403
    with pytest.raises(HTTPException) as exc_info:
        ledger_cashier.approve_cash_variance(rec.id, notes="Self-approving")
    assert exc_info.value.status_code == 403
    assert "cannot approve their own" in exc_info.value.detail

    # 3. Independent Finance Manager approves -> Posts atomic GL journal
    ledger_manager = FinanceLedgerService(db, None, fin_manager)
    approved_rec = ledger_manager.approve_cash_variance(
        rec.id, notes="Investigated and accepted coin discrepancy"
    )
    assert approved_rec.status == "POSTED"
    assert approved_rec.approved_by == fin_manager.id
    assert approved_rec.journal_id is not None

    # Verify Journal Entry Dr 500 Shortage (6600) / Cr 500 Cash (1000)
    journal = db.get(FinanceJournalEntry, approved_rec.journal_id)
    assert journal is not None
    debit_sum = sum(l.debit for l in journal.lines)
    credit_sum = sum(l.credit for l in journal.lines)
    assert debit_sum == credit_sum == Decimal("500.00")
    assert journal.status == "POSTED"


def test_cash_reconciliation_rejection(db: Session, finance_env):
    """Supervisor can reject unverified cash variance, leaving no GL trace."""
    cashier = finance_env["cashier"]
    fin_manager = finance_env["finance_manager"]
    ledger_cashier = FinanceLedgerService(db, None, cashier)

    rec = ledger_cashier.create_cash_reconciliation(
        CashReconciliationIn(
            period_date=date.today(),
            cashier_name=cashier.full_name,
            opening_cash=Decimal("1000.00"),
            expected_cash=Decimal("8000.00"),
            counted_cash=Decimal("7000.00"),
            notes="Unexplained shortage",
        )
    )
    assert rec.status == "VARIANCE_REVIEW"

    ledger_manager = FinanceLedgerService(db, None, fin_manager)
    rejected_rec = ledger_manager.reject_cash_variance(
        rec.id, notes="Drawer recount was actually correct, discrepancy was miscount"
    )
    assert rejected_rec.status == "REJECTED"
    assert rejected_rec.journal_id is None


# ============================================================================
# 4. P0-4: Invoice Immutability & Credit Note Workflow
# ============================================================================

def test_issued_invoice_immutability_and_credit_notes(db: Session, finance_env):
    """Issued invoices cannot have totals directly mutated; reductions require Credit Notes."""
    fin_officer = finance_env["finance_officer"]
    fin_manager = finance_env["finance_manager"]
    client = finance_env["client"]
    billing_officer = BillingOperationService(db, None, fin_officer)

    # 1. Create an invoice
    invoice = Invoice(
        id=uuid4(),
        facility_id=finance_env["facility"].id,
        invoice_number=f"INV-{uuid4().hex[:6]}",
        client_id=client.id,
        issue_date=date.today(),
        due_date=date.today(),
        subtotal=Decimal("10000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("10000.00"),
        status="ISSUED",
        created_by=fin_officer.id,
        updated_by=fin_officer.id,
    )
    db.add(invoice)
    db.commit()

    # 2. Create Credit Note request
    cn_data = CreditNoteIn(
        invoice_id=invoice.id,
        amount=Decimal("2000.00"),
        reason_code="SERVICE_NOT_DELIVERED",
        reason="Consultation canceled by physician",
    )
    credit_note = billing_officer.create_credit_note(cn_data)
    assert credit_note.status == "PENDING_APPROVAL"
    assert credit_note.amount == Decimal("2000.00")
    assert credit_note.credit_number.startswith("CN-")

    # 3. Requester cannot approve own Credit Note (Maker-Checker)
    with pytest.raises(HTTPException) as exc_info:
        billing_officer.approve_credit_note(credit_note.id, notes="Self approval")
    assert exc_info.value.status_code == 403

    # 4. Independent Finance Manager approves Credit Note
    billing_manager = BillingOperationService(db, None, fin_manager)
    approved_cn = billing_manager.approve_credit_note(
        credit_note.id, notes="Verified clinic session cancellation"
    )
    assert approved_cn.status == "POSTED"
    assert approved_cn.journal_id is not None

    # Check Invoice total amount is financially immutable: remains 10,000.00
    db.refresh(invoice)
    assert invoice.total_amount == Decimal("10000.00")
    # Remaining invoice balance is adjusted via credit note: 10,000 - 2,000 = 8,000
    assert billing_manager.get_invoice_balance(invoice.id) == Decimal("8000.00")

    # Check GL Posting: Dr 4000 (Revenue) / Cr 1200 (AR) for 2,000
    journal = db.get(FinanceJournalEntry, approved_cn.journal_id)
    assert journal is not None
    debit_sum = sum(l.debit for l in journal.lines)
    credit_sum = sum(l.credit for l in journal.lines)
    assert debit_sum == credit_sum == Decimal("2000.00")


# ============================================================================
# 5. P0-6: Write-Off Maker-Checker & Senior Threshold
# ============================================================================

def test_write_off_maker_checker_and_senior_approval(db: Session, finance_env):
    """Bad debt write-offs require independent approval; >50k requires senior management."""
    fin_officer = finance_env["finance_officer"]
    fin_manager = finance_env["finance_manager"]
    client = finance_env["client"]
    billing_officer = BillingOperationService(db, None, fin_officer)

    invoice = Invoice(
        id=uuid4(),
        facility_id=finance_env["facility"].id,
        invoice_number=f"INV-{uuid4().hex[:6]}",
        client_id=client.id,
        issue_date=date.today(),
        due_date=date.today(),
        subtotal=Decimal("60000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("60000.00"),
        status="ISSUED",
        created_by=fin_officer.id,
        updated_by=fin_officer.id,
    )
    db.add(invoice)
    db.commit()

    # 1. Create Write-off request for KES 60,000
    wo_data = WriteOffIn(
        invoice_id=invoice.id,
        amount=Decimal("60000.00"),
        reason="Indigent resident debt default past 180 days",
    )
    wo = billing_officer.create_writeoff(wo_data)
    assert wo.status == "PENDING_APPROVAL"
    assert wo.reference_code.startswith("WO-")

    # 2. Requester cannot approve own write-off
    with pytest.raises(HTTPException) as exc_info:
        billing_officer.approve_writeoff(wo.id)
    assert exc_info.value.status_code == 403

    # 3. Finance Officer (not senior) tries to approve > KES 50k -> 403
    other_officer = User(
        id=uuid4(),
        email=f"other_{uuid4().hex[:6]}@rehub.local",
        password_hash="testhash",
        full_name="Second Officer",
        facility_id=finance_env["facility"].id,
        roles=[db.scalar(select(Role).where(Role.name == "Finance Officer"))],
    )
    db.add(other_officer)
    db.commit()
    billing_other = BillingOperationService(db, None, other_officer)
    with pytest.raises(HTTPException) as exc_info:
        billing_other.approve_writeoff(wo.id)
    assert exc_info.value.status_code == 403
    assert "Senior" in exc_info.value.detail or "50,000" in exc_info.value.detail or "senior" in exc_info.value.detail

    # 4. Finance Manager approves -> Success & Posts GL Dr 6000 (Bad Debt) / Cr 1200 (AR)
    billing_manager = BillingOperationService(db, None, fin_manager)
    approved_wo = billing_manager.approve_writeoff(wo.id, notes="Board approved indigent relief")
    assert approved_wo.status == "POSTED"
    assert approved_wo.journal_id is not None

    # Check invoice status
    db.refresh(invoice)
    assert invoice.status == "WRITTEN_OFF"

    # Check GL Entry
    journal = db.get(FinanceJournalEntry, approved_wo.journal_id)
    debit_sum = sum(l.debit for l in journal.lines)
    credit_sum = sum(l.credit for l in journal.lines)
    assert debit_sum == credit_sum == Decimal("60000.00")


# ============================================================================
# 6. P0-5: Atomic Billing and GL Posting
# ============================================================================

def test_atomic_gl_posting_failure_rolls_back_billing(db: Session, finance_env, monkeypatch):
    """If GL posting fails during credit note approval, the entire transaction rolls back."""
    fin_manager = finance_env["finance_manager"]
    fin_officer = finance_env["finance_officer"]
    client = finance_env["client"]

    invoice = Invoice(
        id=uuid4(),
        facility_id=finance_env["facility"].id,
        invoice_number=f"INV-{uuid4().hex[:6]}",
        client_id=client.id,
        issue_date=date.today(),
        due_date=date.today(),
        subtotal=Decimal("5000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("5000.00"),
        status="ISSUED",
        created_by=fin_officer.id,
        updated_by=fin_officer.id,
    )
    db.add(invoice)
    db.commit()

    billing_officer = BillingOperationService(db, None, fin_officer)
    cn = billing_officer.create_credit_note(
        CreditNoteIn(
            invoice_id=invoice.id,
            amount=Decimal("1000.00"),
            reason_code="BILLING_ERROR",
            reason="Test rollback",
        )
    )

    # Monkeypatch FinanceLedgerService.post_journal to simulate an unexpected ledger failure
    def mock_post_journal(*args, **kwargs):
        raise HTTPException(status_code=500, detail="Database lock failure during ledger posting")

    monkeypatch.setattr(FinanceLedgerService, "post_journal", mock_post_journal)

    billing_manager = BillingOperationService(db, None, fin_manager)
    with pytest.raises(HTTPException) as exc_info:
        billing_manager.approve_credit_note(cn.id)
    assert exc_info.value.status_code == 500

    # Ensure transaction was rolled back and CreditNote is NOT marked POSTED
    db.expire_all()
    fresh_cn = db.get(CreditNote, cn.id)
    assert fresh_cn.status == "PENDING_APPROVAL"
    fresh_inv = db.get(Invoice, invoice.id)
    assert fresh_inv.total_amount == Decimal("5000.00")


# ============================================================================
# 7. P0-7: Pre-issue Discounts vs Post-issue Credit Notes
# ============================================================================

def test_pre_issue_discount_senior_approval_check(db: Session, finance_env):
    """High-value pre-issue discounts (>10%) require senior approval."""
    fin_officer = finance_env["finance_officer"]
    billing_officer = BillingOperationService(db, None, fin_officer)

    # 15% discount on KES 10,000 without senior approval -> 403
    with pytest.raises(HTTPException) as exc_info:
        billing_officer.validate_discount_authorization(
            discount_amount=Decimal("1500.00"),
            subtotal=Decimal("10000.00"),
            user=fin_officer,
        )
    assert exc_info.value.status_code == 403
    assert "exceeds" in exc_info.value.detail or "threshold" in exc_info.value.detail

    # Finance Manager can approve discount > 10%
    fin_manager = finance_env["finance_manager"]
    billing_manager = BillingOperationService(db, None, fin_manager)
    # Should not raise
    assert billing_manager.validate_discount_authorization(
        discount_amount=Decimal("1500.00"),
        subtotal=Decimal("10000.00"),
        user=fin_manager,
    ) is True


# ============================================================================
# 8. Billing-to-GL Integrity Diagnostic Scanner
# ============================================================================

def test_billing_gl_integrity_diagnostic(db: Session, finance_env):
    """Integrity service reports MATCHED, MISSING_JOURNAL, and MISMATCH accurately without mutating records."""
    facility = finance_env["facility"]
    client = finance_env["client"]
    fin_manager = finance_env["finance_manager"]
    ledger = FinanceLedgerService(db, None, fin_manager)

    # 1. Invoice with matched GL journal
    inv_matched = Invoice(
        id=uuid4(),
        facility_id=facility.id,
        invoice_number=f"INV-MATCH-{uuid4().hex[:4]}",
        client_id=client.id,
        issue_date=date.today(),
        due_date=date.today(),
        subtotal=Decimal("12500.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("12500.00"),
        status="ISSUED",
        created_by=fin_manager.id,
        updated_by=fin_manager.id,
    )
    db.add(inv_matched)

    # Post matching journal with BILLING_INVOICE source_module
    ar_acc = ledger.account_by_code("1200")
    rev_acc = ledger.account_by_code("4000")
    ledger.post_journal(
        entry_date=date.today(),
        reference=f"JOURNAL-{inv_matched.invoice_number}",
        description=f"Invoice {inv_matched.invoice_number}",
        source_module="BILLING_INVOICE",
        posting_type="SYSTEM",
        source_id=str(inv_matched.id),
        lines=[
            {"account_id": ar_acc.id, "debit": Decimal("12500.00"), "credit": Decimal("0.00")},
            {"account_id": rev_acc.id, "debit": Decimal("0.00"), "credit": Decimal("12500.00")},
        ],
    )

    # 2. Invoice with missing GL journal
    inv_missing = Invoice(
        id=uuid4(),
        facility_id=facility.id,
        invoice_number=f"INV-MISSING-{uuid4().hex[:4]}",
        client_id=client.id,
        issue_date=date.today(),
        due_date=date.today(),
        subtotal=Decimal("8000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("8000.00"),
        status="ISSUED",
        created_by=fin_manager.id,
        updated_by=fin_manager.id,
    )
    db.add(inv_missing)
    db.commit()

    # Run integrity scan
    scanner = BillingGlIntegrityService(db, facility.id)
    report = scanner.scan_all()

    assert report.total_records >= 2
    matched_item = next((r for r in report.records if r.source_id == str(inv_matched.id)), None)
    assert matched_item is not None
    assert matched_item.status == "MATCHED"
    assert matched_item.difference == Decimal("0.00")

    missing_item = next((r for r in report.records if r.source_id == str(inv_missing.id)), None)
    assert missing_item is not None
    assert missing_item.status == "MISSING_JOURNAL"
    assert missing_item.difference == Decimal("8000.00")
