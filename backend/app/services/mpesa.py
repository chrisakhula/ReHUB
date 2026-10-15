"""M-Pesa Daraja production integration service and reconciliation engine."""

import base64
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.config import get_settings
from app.core.system_actor import get_system_actor
from app.models.billing import (
    Invoice,
    MpesaTransaction,
    Payment,
    PaymentAllocation,
)
from app.models.identity import utcnow
from app.services.finance import FinanceLedgerService

logger = logging.getLogger("rehub.mpesa")


def normalize_phone_number(phone: str) -> str:
    """Format phone numbers to Kenyan standard 2547XXXXXXXX or 2541XXXXXXXX."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]
    if digits.startswith("254") and len(digits) == 12:
        return digits
    if len(digits) == 9:
        return "254" + digits
    return digits


class MpesaService:
    def __init__(self, db: Session, actor=None, request=None):
        self.db = db
        self.actor = actor
        self.request = request
        self.settings = get_settings()

    def _get_access_token(self) -> str:
        """Fetch OAuth Bearer token from Safaricom Daraja."""
        consumer_key = self.settings.mpesa_consumer_key
        consumer_secret = self.settings.mpesa_consumer_secret
        if not consumer_key or not consumer_secret:
            raise ValueError("M-Pesa credentials not configured")

        env = self.settings.mpesa_environment.lower()
        base_url = (
            "https://api.safaricom.co.ke"
            if env == "production"
            else "https://sandbox.safaricom.co.ke"
        )
        url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"

        auth_header = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {auth_header}"}

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["access_token"]

    def initiate_stk_push(
        self,
        facility_id: UUID,
        client_id: UUID,
        invoice_id: UUID,
        phone_number: str,
        amount: Decimal,
    ) -> MpesaTransaction:
        """Initiate Daraja STK Push with pre-call transaction recording."""
        # 1. Validate invoice
        invoice = self.db.scalar(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.facility_id == facility_id,
            )
        )
        if not invoice:
            raise HTTPException(404, "Invoice not found or does not belong to facility")
        if invoice.status in ("PAID", "CANCELLED", "WRITTEN_OFF"):
            raise HTTPException(400, f"Invoice cannot accept payment (status: {invoice.status})")

        # Check existing allocations
        allocated = self.db.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                PaymentAllocation.invoice_id == invoice_id
            )
        ) or Decimal("0.00")
        remaining = Decimal(str(invoice.total_amount)) - Decimal(str(allocated))
        if amount > remaining:
            raise HTTPException(
                400,
                f"Requested amount ({amount}) exceeds remaining invoice balance ({remaining})",
            )

        formatted_phone = normalize_phone_number(phone_number)
        req_ref = f"STK-{uuid4().hex[:12].upper()}"

        # 2. Pre-create transaction record before calling external service
        tx = MpesaTransaction(
            facility_id=facility_id,
            client_id=client_id,
            invoice_id=invoice_id,
            payer_id=invoice.payer_id,
            transaction_reference=req_ref,
            phone_number=formatted_phone,
            amount=amount,
            timestamp=utcnow(),
            status="REQUESTED",
            reconciliation_status="UNMATCHED",
            raw_payload="",
        )
        self.db.add(tx)
        self.db.flush()

        # 3. Call Safaricom Daraja STK Push or mock simulation
        is_live_configured = bool(
            self.settings.mpesa_consumer_key
            and self.settings.mpesa_consumer_secret
            and self.settings.mpesa_passkey
            and self.settings.mpesa_shortcode
        )

        if not is_live_configured:
            # Simulated response for sandbox testing / unconfigured credentials
            logger.info("M-Pesa credentials not configured. Executing simulated STK push.")
            merchant_request_id = f"SIM-MERCHANT-{uuid4().hex[:8]}"
            checkout_request_id = f"ws_CO_{datetime.utcnow().strftime('%d%m%Y%H%M%S')}_{uuid4().hex[:6]}"
            tx.merchant_request_id = merchant_request_id
            tx.checkout_request_id = checkout_request_id
            tx.response_code = "0"
            tx.customer_message = "Success. Request accepted for processing (Simulated)"
            tx.status = "PENDING"
            self.db.commit()
            return tx

        try:
            token = self._get_access_token()
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            shortcode = self.settings.mpesa_shortcode
            passkey = self.settings.mpesa_passkey
            password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

            env = self.settings.mpesa_environment.lower()
            base_url = (
                "https://api.safaricom.co.ke"
                if env == "production"
                else "https://sandbox.safaricom.co.ke"
            )
            stk_url = f"{base_url}/mpesa/stkpush/v1/processrequest"

            callback_url = (
                self.settings.mpesa_callback_url
                or f"{self.settings.public_app_url}/api/v1/billing/mpesa/callback"
            )

            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": formatted_phone,
                "PartyB": shortcode,
                "PhoneNumber": formatted_phone,
                "CallBackURL": callback_url,
                "AccountReference": invoice.invoice_number[:12],
                "TransactionDesc": f"Payment for {invoice.invoice_number}",
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            with httpx.Client(timeout=20.0) as client:
                res = client.post(stk_url, json=payload, headers=headers)
                data = res.json()

            tx.merchant_request_id = data.get("MerchantRequestID")
            tx.checkout_request_id = data.get("CheckoutRequestID")
            tx.response_code = str(data.get("ResponseCode", ""))
            tx.customer_message = data.get("CustomerMessage") or data.get("ResponseDescription")
            tx.raw_payload = str(data)

            if tx.response_code == "0":
                tx.status = "PENDING"
            else:
                tx.status = "FAILED"
                tx.reconciliation_status = "FAILED"

            self.db.commit()
            return tx
        except Exception as exc:
            logger.error("Error communicating with Daraja STK Push: %s", exc)
            tx.status = "FAILED"
            tx.reconciliation_status = "FAILED"
            tx.customer_message = f"Failed to initiate: {str(exc)}"
            self.db.commit()
            raise HTTPException(502, f"Failed to connect to M-Pesa provider: {str(exc)}")

    def process_callback(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Process Daraja STK Callback or C2B webhook with strict idempotency and GL posting."""
        logger.info("Processing M-Pesa callback: %s", raw_data)

        # 1. Parse STK Callback format or C2B format
        checkout_req_id: Optional[str] = None
        merchant_req_id: Optional[str] = None
        result_code: int = -1
        result_desc: str = ""
        receipt_number: Optional[str] = None
        amount: Optional[Decimal] = None
        phone: Optional[str] = None
        bill_ref: Optional[str] = None

        if "Body" in raw_data and "stkCallback" in raw_data["Body"]:
            cb = raw_data["Body"]["stkCallback"]
            merchant_req_id = cb.get("MerchantRequestID")
            checkout_req_id = cb.get("CheckoutRequestID")
            result_code = int(cb.get("ResultCode", -1))
            result_desc = cb.get("ResultDesc", "")

            meta = cb.get("CallbackMetadata", {}).get("Item", [])
            for item in meta:
                name = item.get("Name")
                val = item.get("Value")
                if name == "MpesaReceiptNumber":
                    receipt_number = str(val)
                elif name == "Amount":
                    amount = Decimal(str(val))
                elif name == "PhoneNumber":
                    phone = str(val)
        elif "TransID" in raw_data:
            # C2B webhook format
            receipt_number = raw_data.get("TransID")
            amount = Decimal(str(raw_data.get("TransAmount", "0")))
            phone = raw_data.get("MSISDN")
            bill_ref = raw_data.get("BillRefNumber")
            result_code = 0
            result_desc = "Accepted"
        else:
            logger.warning("Unrecognized M-Pesa callback payload format")
            return {"ResultCode": 1, "ResultDesc": "Invalid payload format"}

        # 2. Find matching transaction
        tx: Optional[MpesaTransaction] = None
        if checkout_req_id:
            tx = self.db.scalar(
                select(MpesaTransaction).where(
                    MpesaTransaction.checkout_request_id == checkout_req_id
                )
            )

        if not tx and receipt_number:
            tx = self.db.scalar(
                select(MpesaTransaction).where(
                    MpesaTransaction.transaction_reference == receipt_number
                )
            )

        # 3. Idempotency Guard: repeated callback
        if tx and tx.status in ("SUCCESS", "RECONCILED") and tx.reconciliation_status == "AUTO_RECONCILED":
            logger.info("Transaction %s already reconciled. Skipping repeated callback.", tx.id)
            return {"ResultCode": 0, "ResultDesc": "Already processed"}

        system_actor = get_system_actor(self.db, tx.facility_id if tx else None)

        # 4. Handle Failure Cases
        if result_code != 0:
            if tx:
                tx.status = "CANCELLED" if result_code in (1032, 1037) else "FAILED"
                tx.reconciliation_status = "FAILED"
                tx.customer_message = result_desc
                tx.raw_payload = str(raw_data)
                self.db.commit()
            return {"ResultCode": 0, "ResultDesc": "Callback handled with non-zero result code"}

        # 5. Handle Successful Payment
        if not tx:
            # Webhook received without pre-existing STK push (e.g. direct Paybill)
            facility_id = system_actor.facility_id
            tx = MpesaTransaction(
                facility_id=facility_id,
                transaction_reference=receipt_number or f"MPESA-{uuid4().hex[:10].upper()}",
                phone_number=phone or "",
                amount=amount or Decimal("0.00"),
                timestamp=utcnow(),
                status="SUCCESS",
                reconciliation_status="UNMATCHED",
                raw_payload=str(raw_data),
            )
            self.db.add(tx)
            self.db.flush()

            # Attempt auto-match via BillRefNumber
            if bill_ref:
                invoice = self.db.scalar(
                    select(Invoice).where(
                        Invoice.invoice_number == bill_ref.strip(),
                        Invoice.facility_id == facility_id,
                    )
                )
                if invoice:
                    tx.invoice_id = invoice.id
                    tx.client_id = invoice.client_id
                    tx.payer_id = invoice.payer_id

        # Update transaction record
        if receipt_number:
            tx.transaction_reference = receipt_number
        if amount:
            tx.amount = amount
        tx.status = "SUCCESS"
        tx.raw_payload = str(raw_data)

        # 6. Atomic payment creation and invoice allocation
        invoice: Optional[Invoice] = None
        if tx.invoice_id:
            invoice = self.db.get(Invoice, tx.invoice_id)

        if invoice and invoice.status not in ("PAID", "CANCELLED", "WRITTEN_OFF"):
            payment = Payment(
                facility_id=invoice.facility_id,
                payer_id=invoice.payer_id,
                client_id=invoice.client_id,
                amount=tx.amount,
                payment_method="MPESA",
                transaction_reference=tx.transaction_reference,
                payment_date=utcnow(),
                status="COMPLETED",
                created_by=system_actor.id,
                updated_by=system_actor.id,
            )
            self.db.add(payment)
            self.db.flush()

            alloc = PaymentAllocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount=tx.amount,
                allocated_at=utcnow(),
                allocated_by=system_actor.id,
                created_by=system_actor.id,
                updated_by=system_actor.id,
            )
            self.db.add(alloc)

            tx.reconciled_payment_id = payment.id
            tx.reconciliation_status = "AUTO_RECONCILED"
            tx.reconciled_at = utcnow()

            # Recalculate invoice status
            total_allocated = self.db.scalar(
                select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                    PaymentAllocation.invoice_id == invoice.id
                )
            ) or Decimal("0.00")

            if Decimal(str(total_allocated)) >= Decimal(str(invoice.total_amount)):
                invoice.status = "PAID"
            elif Decimal(str(total_allocated)) > Decimal("0.00"):
                invoice.status = "PARTIAL"

            # 7. Post to General Ledger (Dr M-Pesa Control 1010, Cr Accounts Receivable 1200)
            try:
                ledger_svc = FinanceLedgerService(self.db, None, system_actor)
                ledger_svc.post_journal(
                    entry_date=datetime.utcnow().date(),
                    reference=f"MPESA-{tx.transaction_reference}",
                    description=f"M-Pesa payment {tx.transaction_reference} for {invoice.invoice_number}",
                    source_module="BILLING_MPESA",
                    source_id=str(tx.id),
                    posting_type="PAYMENT",
                    lines=[
                        {"account_code": "1010", "debit": tx.amount, "credit": 0},
                        {"account_code": "1200", "debit": 0, "credit": tx.amount},
                    ],
                )
            except Exception as e:
                logger.error("Failed to post journal entry for M-Pesa payment: %s", e)
        else:
            tx.reconciliation_status = "UNMATCHED"

        self.db.commit()
        return {"ResultCode": 0, "ResultDesc": "Processed"}

    def allocate_unmatched_transaction(
        self,
        transaction_id: UUID,
        invoice_id: UUID,
        notes: str = "",
    ) -> MpesaTransaction:
        """Manually allocate an unmatched or manual-review M-Pesa transaction to an invoice."""
        tx = self.db.get(MpesaTransaction, transaction_id)
        if not tx:
            raise HTTPException(404, "M-Pesa transaction not found")
        if tx.reconciliation_status == "AUTO_RECONCILED" and tx.reconciled_payment_id:
            raise HTTPException(400, "Transaction is already reconciled")

        invoice = self.db.get(Invoice, invoice_id)
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        if invoice.status in ("PAID", "CANCELLED", "WRITTEN_OFF"):
            raise HTTPException(400, f"Invoice cannot accept payment (status: {invoice.status})")

        actor = self.actor or get_system_actor(self.db, tx.facility_id)

        # Create payment
        payment = Payment(
            facility_id=invoice.facility_id,
            payer_id=invoice.payer_id,
            client_id=invoice.client_id,
            amount=tx.amount,
            payment_method="MPESA",
            transaction_reference=tx.transaction_reference,
            payment_date=utcnow(),
            status="COMPLETED",
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(payment)
        self.db.flush()

        alloc = PaymentAllocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            amount=tx.amount,
            allocated_at=utcnow(),
            allocated_by=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(alloc)

        # Update invoice
        total_allocated = self.db.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                PaymentAllocation.invoice_id == invoice.id
            )
        ) or Decimal("0.00")

        if Decimal(str(total_allocated)) >= Decimal(str(invoice.total_amount)):
            invoice.status = "PAID"
        elif Decimal(str(total_allocated)) > Decimal("0.00"):
            invoice.status = "PARTIAL"

        # Update M-Pesa transaction
        tx.client_id = invoice.client_id
        tx.invoice_id = invoice.id
        tx.payer_id = invoice.payer_id
        tx.reconciled_payment_id = payment.id
        tx.reconciliation_status = "MANUAL_REVIEW"
        tx.reconciled_by_id = actor.id
        tx.reconciled_at = utcnow()
        tx.reconciliation_notes = notes

        # Post to General Ledger
        try:
            ledger_svc = FinanceLedgerService(self.db, self.request, actor)
            ledger_svc.post_journal(
                entry_date=datetime.utcnow().date(),
                reference=f"MPESA-{tx.transaction_reference}",
                description=f"Manual M-Pesa allocation {tx.transaction_reference} to {invoice.invoice_number}",
                source_module="BILLING_MPESA",
                source_id=str(tx.id),
                posting_type="MANUAL_ALLOCATION",
                lines=[
                    {"account_code": "1010", "debit": tx.amount, "credit": 0},
                    {"account_code": "1200", "debit": 0, "credit": tx.amount},
                ],
            )
        except Exception as e:
            logger.error("Failed to post journal entry for manual allocation: %s", e)

        self.db.commit()
        if self.request:
            audit(
                self.db,
                self.request,
                "billing.mpesa_manual_reconciled",
                "MpesaTransaction",
                actor,
                tx.id,
                new={"invoice_id": str(invoice.id), "amount": str(tx.amount)},
            )
        return tx
