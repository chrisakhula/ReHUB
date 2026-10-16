"""Automated test suite for Sprint D: Financial Integrity Hardening, Double-Entry Balancing, and Segregation of Duties."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finance import (
    FinanceAccount,
    FinanceExpenseCategory,
    FinanceExpenseVoucher,
    FinanceFiscalPeriod,
    FinanceJournalEntry,
)
from app.models.identity import Facility, Permission, Role, User
from app.schemas.finance import ExpenseVoucherIn, ManualJournalIn
from app.services.finance import FinanceLedgerService, money


@pytest.fixture
def finance_setup(db: Session):
    facility = db.scalars(select(Facility)).first()

    clerk_email = f"clerk_{uuid4().hex[:6]}@rehub.local"
    clerk = User(
        id=uuid4(),
        email=clerk_email,
        password_hash="argon2id$clerk_hash",
        full_name="Faith Wangari (Finance Clerk)",
        facility_id=facility.id,
        active=True,
    )
    db.add(clerk)

    # User 2: Finance Approver (Checker)
    approver_email = f"approver_{uuid4().hex[:6]}@rehub.local"
    approver = User(
        id=uuid4(),
        email=approver_email,
        password_hash="argon2id$approver_hash",
        full_name="Samuel Ochieng (Finance Officer)",
        facility_id=facility.id,
        active=True,
    )
    perm_app = db.scalar(select(Permission).where(Permission.code == "finance.approve"))
    if not perm_app:
        perm_app = Permission(id=uuid4(), code="finance.approve", description="Approve finance")
        db.add(perm_app)
    approver.permissions.append(perm_app)
    db.add(approver)

    # User 3: Senior Finance Director
    senior_email = f"director_{uuid4().hex[:6]}@rehub.local"
    senior = User(
        id=uuid4(),
        email=senior_email,
        password_hash="argon2id$senior_hash",
        full_name="Catherine Mutua (Chief Financial Officer)",
        facility_id=facility.id,
        active=True,
    )
    perm_cfg = db.scalar(select(Permission).where(Permission.code == "finance.configure"))
    if not perm_cfg:
        perm_cfg = Permission(
            id=uuid4(),
            code="finance.configure",
            description="Configure Finance and Periods",
        )
        db.add(perm_cfg)
    senior.permissions.append(perm_cfg)
    db.add(senior)
    db.commit()

    # Seed chart of accounts for facility
    ledger = FinanceLedgerService(db, None, clerk)
    ledger.seed_defaults()
    db.commit()

    return facility, clerk, approver, senior


def test_double_entry_balancing_enforcement(db: Session, finance_setup):
    facility, clerk, _, _ = finance_setup
    ledger = FinanceLedgerService(db, None, clerk)

    cash_acc = ledger.account_by_code("1000")
    rev_acc = ledger.account_by_code("4000")

    # 1. Unbalanced journal: Debit 5,000 vs Credit 4,500
    with pytest.raises(HTTPException) as exc_info:
        ledger.post_journal(
            entry_date=date.today(),
            reference="TEST-UNBAL-01",
            description="Unbalanced entry test",
            source_module="TEST",
            posting_type="MANUAL",
            source_id="TEST-1",
            lines=[
                {"account_id": cash_acc.id, "debit": Decimal("5000.00"), "credit": Decimal("0.00")},
                {"account_id": rev_acc.id, "debit": Decimal("0.00"), "credit": Decimal("4500.00")},
            ],
        )
    assert exc_info.value.status_code == 422
    assert "unbalanced" in exc_info.value.detail.lower()

    # 2. Balanced journal: Debit 5,000 vs Credit 5,000
    entry = ledger.post_journal(
        entry_date=date.today(),
        reference="TEST-BAL-01",
        description="Balanced entry test",
        source_module="TEST",
        posting_type="MANUAL",
        source_id="TEST-2",
        lines=[
            {"account_id": cash_acc.id, "debit": Decimal("5000.00"), "credit": Decimal("0.00")},
            {"account_id": rev_acc.id, "debit": Decimal("0.00"), "credit": Decimal("5000.00")},
        ],
    )
    assert entry is not None
    assert entry.status == "POSTED"
    db.commit()


def test_fiscal_period_controls_and_audit_reopen(db: Session, finance_setup):
    facility, clerk, _, senior = finance_setup
    ledger = FinanceLedgerService(db, None, clerk)

    # Find the current period and lock it
    today = date.today()
    period = db.scalar(
        select(FinanceFiscalPeriod).filter(
            FinanceFiscalPeriod.facility_id == facility.id,
            FinanceFiscalPeriod.start_date <= today,
            FinanceFiscalPeriod.end_date >= today,
        )
    )
    assert period is not None

    cash_acc = ledger.account_by_code("1000")
    rev_acc = ledger.account_by_code("4000")

    # 1. Lock period -> ordinary posting must fail with 409
    period.status = "LOCKED"
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        ledger.post_journal(
            entry_date=today,
            reference="TEST-LOCKED-01",
            description="Posting to locked period",
            source_module="TEST",
            posting_type="MANUAL",
            source_id=None,
            lines=[
                {"account_id": cash_acc.id, "debit": Decimal("100.00"), "credit": 0},
                {"account_id": rev_acc.id, "debit": 0, "credit": Decimal("100.00")},
            ],
        )
    assert exc_info.value.status_code == 409
    assert "locked" in exc_info.value.detail.lower()

    # 2. Close period -> posting strictly prohibited
    period.status = "CLOSED"
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        ledger.post_journal(
            entry_date=today,
            reference="TEST-CLOSED-01",
            description="Posting to closed period",
            source_module="TEST",
            posting_type="MANUAL",
            source_id=None,
            lines=[
                {"account_id": cash_acc.id, "debit": Decimal("100.00"), "credit": 0},
                {"account_id": rev_acc.id, "debit": 0, "credit": Decimal("100.00")},
            ],
        )
    assert exc_info.value.status_code == 409
    assert "closed" in exc_info.value.detail.lower()

    # 3. Attempt to reopen without required audit justification (or < 10 chars)
    senior_ledger = FinanceLedgerService(db, None, senior)
    with pytest.raises(HTTPException) as exc_info:
        senior_ledger.set_period_status(period.id, "OPEN", reason="short")
    assert exc_info.value.status_code == 422
    assert "reason" in exc_info.value.detail.lower()

    # 4. Valid audit reopening by senior authority
    reopened = senior_ledger.set_period_status(
        period.id, "OPEN", reason="Reopening for formal year-end audit adjustments and accrual postings"
    )
    assert reopened.status == "OPEN"
    db.commit()


def test_segregation_of_duties_enforcement(db: Session, finance_setup):
    facility, clerk, approver, _ = finance_setup

    clerk_ledger = FinanceLedgerService(db, None, clerk)
    approver_ledger = FinanceLedgerService(db, None, approver)

    # 1. Clerk creates an expense voucher
    cat = db.scalar(select(FinanceExpenseCategory).filter(FinanceExpenseCategory.facility_id == facility.id))
    assert cat is not None

    voucher = clerk_ledger.create_expense(
        ExpenseVoucherIn(
            expense_category_id=cat.id,
            amount=Decimal("15000.00"),
            payment_method="CASH",
            paid_to="Nairobi Water Company",
            reference="WATER-2026-OCT",
            description="Monthly facility water bill",
            expense_date=date.today(),
        )
    )
    db.commit()

    # 2. Clerk attempts to self-approve the voucher -> Segregation of Duties violation!
    with pytest.raises(HTTPException) as exc_info:
        clerk_ledger.approve_expense(voucher.id)
    assert exc_info.value.status_code == 403
    assert "segregation of duties" in exc_info.value.detail.lower()

    # 3. Independent checker (approver) approves voucher -> Success!
    approved_voucher = approver_ledger.approve_expense(voucher.id)
    assert approved_voucher.status == "APPROVED"
    assert approved_voucher.approved_by == approver.id
    db.commit()


def test_configurable_senior_finance_approval_threshold(db: Session, finance_setup):
    facility, clerk, approver, senior = finance_setup

    clerk_ledger = FinanceLedgerService(db, None, clerk)
    approver_ledger = FinanceLedgerService(db, None, approver)
    senior_ledger = FinanceLedgerService(db, None, senior)

    cat = db.scalar(select(FinanceExpenseCategory).filter(FinanceExpenseCategory.facility_id == facility.id))

    # Create a high-value expense exceeding KSh 50,000 (e.g. KSh 85,000 for generator maintenance)
    high_val_voucher = clerk_ledger.create_expense(
        ExpenseVoucherIn(
            expense_category_id=cat.id,
            amount=Decimal("85000.00"),
            payment_method="MPESA",
            paid_to="Kenya Power & Generators Ltd",
            reference="GEN-REPAIR-001",
            description="Major diesel generator motor overhaul",
            expense_date=date.today(),
        )
    )
    db.commit()

    # 1. Regular approver attempts to approve high-value expense (> KSh 50,000)
    with pytest.raises(HTTPException) as exc_info:
        approver_ledger.approve_expense(high_val_voucher.id)
    assert exc_info.value.status_code == 403
    assert "senior finance authorization" in exc_info.value.detail.lower()

    # 2. Senior Finance Officer approves high-value expense -> Success!
    approved = senior_ledger.approve_expense(high_val_voucher.id)
    assert approved.status == "APPROVED"
    assert approved.approved_by == senior.id
    db.commit()


def test_non_destructive_journal_reversal(db: Session, finance_setup):
    facility, clerk, approver, _ = finance_setup
    ledger = FinanceLedgerService(db, None, clerk)
    approver_ledger = FinanceLedgerService(db, None, approver)

    cash_acc = ledger.account_by_code("1000")
    rev_acc = ledger.account_by_code("4000")

    # Post an entry
    original = ledger.post_journal(
        entry_date=date.today(),
        reference="JOURNAL-ORIG-99",
        description="Original posted journal entry",
        source_module="FINANCE",
        posting_type="MANUAL",
        source_id="ORIG-99",
        lines=[
            {"account_id": cash_acc.id, "debit": Decimal("12000.00"), "credit": 0},
            {"account_id": rev_acc.id, "debit": 0, "credit": Decimal("12000.00")},
        ],
    )
    db.commit()

    # Reversal creates a balancing correcting journal rather than destructively deleting original
    reversal = approver_ledger.reverse_journal(original.id)
    assert reversal is not None
    assert reversal.status == "POSTED"
    assert reversal.reversed_entry_id == original.id

    db.refresh(original)
    assert original.status == "REVERSED"
