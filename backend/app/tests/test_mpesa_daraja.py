"""Integration tests for M-Pesa Daraja production layer, system actor attribution, and reconciliation."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.billing import Invoice, MpesaTransaction, Payment, PaymentAllocation
from app.models.clients import Client
from app.models.finance import FinanceJournalEntry, FinanceJournalLine
from app.models.identity import Facility, User
from app.services.finance import FinanceLedgerService
from app.services.mpesa import MpesaService, normalize_phone_number


def test_normalize_phone_number():
    assert normalize_phone_number("0712345678") == "254712345678"
    assert normalize_phone_number("254712345678") == "254712345678"
    assert normalize_phone_number("+254712345678") == "254712345678"
    assert normalize_phone_number("712345678") == "254712345678"


def login_as_finance(db, client):
    user = db.scalar(select(User).where(User.email == "finance@example.org"))
    user.force_password_change = False
    db.commit()
    resp = client.post("/api/v1/auth/login", json={"email": "finance@example.org", "password": "ChangeMe!2026"})
    assert resp.status_code == 200, resp.text
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")
    return client


def test_mpesa_stk_push_and_callback_flow(db, client):
    finance_client = login_as_finance(db, client)
    # Ensure chart of accounts and current fiscal period exist
    admin = db.scalar(select(User).where(User.email == "admin@example.org"))
    ledger_svc = FinanceLedgerService(db, None, admin)
    ledger_svc.seed_defaults()
    db.commit()

    # Create client
    client_rec = Client(
        facility_id=admin.facility_id,
        client_number=f"CL-{uuid4().hex[:6].upper()}",
        first_name="Jane",
        surname="Wanjiru",
        date_of_birth=date(1992, 5, 14),
        sex="FEMALE",
        national_id=f"ID-{uuid4().hex[:6]}",
        created_by=admin.id,
        updated_by=admin.id,
    )
    db.add(client_rec)
    db.flush()

    # Create invoice
    invoice = Invoice(
        facility_id=admin.facility_id,
        client_id=client_rec.id,
        invoice_number=f"INV-{uuid4().hex[:6].upper()}",
        issue_date=date.today(),
        due_date=date.today(),
        status="ISSUED",
        subtotal=5000.00,
        discount_amount=0.00,
        tax_amount=0.00,
        total_amount=5000.00,
        created_by=admin.id,
        updated_by=admin.id,
    )
    db.add(invoice)
    db.commit()

    # 1. Initiate STK Push via API
    stk_resp = finance_client.post(
        "/api/v1/billing/mpesa/stk-push",
        json={
            "client_id": str(client_rec.id),
            "invoice_id": str(invoice.id),
            "phone_number": "0712345678",
            "amount": 5000.00,
        },
    )
    assert stk_resp.status_code == 200, stk_resp.text
    tx_data = stk_resp.json()
    assert tx_data["status"] == "PENDING"
    assert tx_data["checkout_request_id"] is not None
    checkout_id = tx_data["checkout_request_id"]
    receipt_no = f"QWE{uuid4().hex[:7].upper()}"

    # 2. Simulate Safaricom STK Callback
    callback_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": tx_data["merchant_request_id"],
                "CheckoutRequestID": checkout_id,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 5000.00},
                        {"Name": "MpesaReceiptNumber", "Value": receipt_no},
                        {"Name": "TransactionDate", "Value": 20261012120000},
                        {"Name": "PhoneNumber", "Value": 254712345678},
                    ]
                },
            }
        }
    }

    # Public callback (no cookies/auth needed)
    cb_resp = client.post("/api/v1/billing/mpesa/callback", json=callback_payload)
    assert cb_resp.status_code == 200
    assert cb_resp.json()["ResultCode"] == 0

    # 3. Verify Database Records
    db.expire_all()
    tx = db.scalar(select(MpesaTransaction).where(MpesaTransaction.checkout_request_id == checkout_id))
    assert tx is not None
    assert tx.status == "SUCCESS"
    assert tx.reconciliation_status == "AUTO_RECONCILED"
    assert tx.transaction_reference == receipt_no
    assert tx.reconciled_payment_id is not None

    # Verify payment record attributed to System Integration Actor
    payment = db.get(Payment, tx.reconciled_payment_id)
    assert payment is not None
    assert payment.amount == Decimal("5000.00")
    assert payment.status == "COMPLETED"
    assert payment.payment_method == "MPESA"

    system_user = db.get(User, payment.created_by)
    assert system_user.email == "system.integration@rehub.local"

    # Verify Invoice was updated to PAID
    inv = db.get(Invoice, invoice.id)
    assert inv.status == "PAID"

    # Verify GL Journal Entry was posted (Dr 1010 / Cr 1200)
    journal = db.scalar(
        select(FinanceJournalEntry).where(
            FinanceJournalEntry.source_module == "BILLING_MPESA",
            FinanceJournalEntry.source_id == str(tx.id),
        )
    )
    assert journal is not None
    lines = db.scalars(
        select(FinanceJournalLine).where(FinanceJournalLine.journal_entry_id == journal.id)
    ).all()
    assert len(lines) == 2
    debit_line = next(line for line in lines if line.debit > 0)
    credit_line = next(line for line in lines if line.credit > 0)
    assert debit_line.debit == Decimal("5000.00")
    assert credit_line.credit == Decimal("5000.00")

    # 4. Idempotency Test: Repeat identical callback
    cb_resp_repeat = client.post("/api/v1/billing/mpesa/callback", json=callback_payload)
    assert cb_resp_repeat.status_code == 200
    assert "Already processed" in cb_resp_repeat.json()["ResultDesc"]

    # Verify no duplicate payments or journals were created
    payments = db.scalars(select(Payment).where(Payment.transaction_reference == receipt_no)).all()
    assert len(payments) == 1


def test_manual_mpesa_reconciliation(db, client):
    finance_client = login_as_finance(db, client)
    admin = db.scalar(select(User).where(User.email == "admin@example.org"))
    ledger_svc = FinanceLedgerService(db, None, admin)
    ledger_svc.seed_defaults()
    db.commit()

    # Create client & invoice
    client_rec = Client(
        facility_id=admin.facility_id,
        client_number=f"CL-{uuid4().hex[:6].upper()}",
        first_name="Mark",
        surname="Otieno",
        date_of_birth=date(1985, 3, 20),
        sex="MALE",
        national_id=f"ID-{uuid4().hex[:6]}",
        created_by=admin.id,
        updated_by=admin.id,
    )
    db.add(client_rec)
    db.flush()

    invoice = Invoice(
        facility_id=admin.facility_id,
        client_id=client_rec.id,
        invoice_number=f"INV-{uuid4().hex[:6].upper()}",
        issue_date=date.today(),
        due_date=date.today(),
        status="ISSUED",
        subtotal=2500.00,
        discount_amount=0.00,
        tax_amount=0.00,
        total_amount=2500.00,
        created_by=admin.id,
        updated_by=admin.id,
    )
    db.add(invoice)
    db.commit()

    # Create an unmatched transaction (e.g. client paid via paybill without bill reference)
    unmatched_ref = f"MANUAL-{uuid4().hex[:8].upper()}"
    tx = MpesaTransaction(
        facility_id=admin.facility_id,
        transaction_reference=unmatched_ref,
        phone_number="254700112233",
        amount=Decimal("2500.00"),
        timestamp=datetime.utcnow(),
        status="SUCCESS",
        reconciliation_status="UNMATCHED",
        raw_payload="{}",
    )
    db.add(tx)
    db.commit()

    # Call manual allocation endpoint
    resp = finance_client.post(
        f"/api/v1/billing/mpesa/reconciliation/{tx.id}/allocate",
        json={
            "invoice_id": str(invoice.id),
            "notes": "Allocated after phone verification with client family.",
        },
    )
    assert resp.status_code == 200, resp.text
    allocated_tx = resp.json()
    assert allocated_tx["reconciliation_status"] == "MANUAL_REVIEW"
    assert allocated_tx["reconciled_payment_id"] is not None

    # Verify invoice is paid
    db.expire_all()
    inv = db.get(Invoice, invoice.id)
    assert inv.status == "PAID"
