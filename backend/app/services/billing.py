"""Billing service: Invoicing, payments, credit notes, write-offs, and atomic GL posting."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import get_settings
from app.core.money import money
from app.core.reference_generator import generate_reference_code
from app.audit.service import audit
from app.models.billing import (
    Invoice,
    InvoiceItem,
    Payment,
    PaymentAllocation,
    Payer,
    PriceList,
    CreditNote,
    Refund,
    Adjustment,
    WriteOff,
    MpesaTransaction,
)
from app.schemas.billing import (
    InvoiceIn,
    PaymentIn,
    CreditNoteIn,
    WriteOffIn,
)
from app.services.finance import FinanceLedgerService, PAYMENT_ACCOUNT_BY_METHOD

logger = logging.getLogger("rehub.billing")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FinanceService:
    def __init__(self, db: Session, request, actor):
        self.db = db
        self.request = request
        self.actor = actor
        self.facility_id = actor.facility_id

    def event(self, action: str, entity, new: dict = None, previous: dict = None, reason: str = ""):
        audit(self.db, self.request, action, entity.__class__.__name__, self.actor, getattr(entity, "id", None))

    def create_invoice(self, data: InvoiceIn) -> Invoice:
        invoice_num = data.invoice_number or generate_reference_code(
            self.db, self.facility_id, "INVOICE"
        )
        invoice = Invoice(
            facility_id=self.facility_id,
            client_id=data.client_id,
            admission_id=data.admission_id,
            payer_id=data.payer_id,
            invoice_number=invoice_num,
            issue_date=data.issue_date,
            due_date=data.due_date,
            status=data.status,
            notes=data.notes,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(invoice)
        self.db.flush()

        subtotal = Decimal("0.00")
        tax = Decimal("0.00")
        discount = Decimal("0.00")

        payer_category = "PRIVATE"
        if data.payer_id:
            payer = self.db.query(Payer).filter(Payer.id == data.payer_id).first()
            if payer:
                payer_category = payer.payer_type

        for item_in in data.items:
            unit_price = money(item_in.unit_price)

            # Enforce canonical price
            if item_in.service_id or item_in.package_id:
                price_query = self.db.query(PriceList).filter(
                    PriceList.facility_id == self.facility_id,
                    PriceList.is_active == True,
                    PriceList.payer_category == payer_category,
                )
                if item_in.service_id:
                    price_query = price_query.filter(PriceList.service_id == item_in.service_id)
                elif item_in.package_id:
                    price_query = price_query.filter(PriceList.package_id == item_in.package_id)

                price_record = price_query.order_by(PriceList.effective_from.desc()).first()

                # Fallback to DEFAULT category if specific payer category price is not found
                if not price_record and payer_category != "DEFAULT":
                    price_query_default = self.db.query(PriceList).filter(
                        PriceList.facility_id == self.facility_id,
                        PriceList.is_active == True,
                        PriceList.payer_category == "DEFAULT",
                    )
                    if item_in.service_id:
                        price_query_default = price_query_default.filter(PriceList.service_id == item_in.service_id)
                    elif item_in.package_id:
                        price_query_default = price_query_default.filter(PriceList.package_id == item_in.package_id)
                    price_record = price_query_default.order_by(PriceList.effective_from.desc()).first()

                if price_record:
                    unit_price = money(price_record.amount)

            item_qty = money(item_in.quantity)
            item_discount = money(item_in.discount)
            item_subtotal = money(item_qty * unit_price)
            taxable_base = max(Decimal("0.00"), item_subtotal - item_discount)
            item_tax_rate = money(item_in.tax_rate)
            item_tax = money(taxable_base * (item_tax_rate / Decimal("100.00")))
            item_total = taxable_base + item_tax

            item = InvoiceItem(
                invoice_id=invoice.id,
                service_id=item_in.service_id,
                package_id=item_in.package_id,
                description=item_in.description,
                quantity=item_qty,
                unit_price=unit_price,
                discount=item_discount,
                tax_rate=item_tax_rate,
                total_price=item_total,
                created_by=self.actor.id,
                updated_by=self.actor.id,
            )
            self.db.add(item)

            subtotal += item_subtotal
            discount += item_discount
            tax += item_tax

        # Validate senior discount approval threshold if invoice is not draft
        if invoice.status != "DRAFT":
            self.validate_discount_authorization(discount, subtotal)

        invoice.subtotal = subtotal
        invoice.discount_amount = discount
        invoice.tax_amount = tax
        invoice.total_amount = max(Decimal("0.00"), subtotal - discount + tax)

        self.db.flush()
        self.event("billing.invoice_created", invoice)

        # Atomic GL Posting: Dr Accounts Receivable (1200) / Cr Patient Service Revenue (4000)
        # Never swallow exceptions! Failure to post must reject/rollback the invoice.
        if invoice.status in ("ISSUED", "PARTIAL", "PAID") and invoice.total_amount > Decimal("0.00"):
            ledger = FinanceLedgerService(self.db, self.request, self.actor)
            ledger.post_journal(
                entry_date=invoice.issue_date,
                reference=invoice.invoice_number,
                description=f"Invoice {invoice.invoice_number}",
                source_module="BILLING_INVOICE",
                source_id=str(invoice.id),
                posting_type="INVOICE",
                lines=[
                    {"account_code": "1200", "debit": invoice.total_amount, "credit": Decimal("0.00")},
                    {"account_code": "4000", "debit": Decimal("0.00"), "credit": invoice.total_amount},
                ],
            )

        return invoice

    def validate_discount_authorization(
        self, discount_amount: Decimal, subtotal: Decimal, user=None
    ) -> bool:
        target_user = user or self.actor
        settings = get_settings()
        if subtotal > Decimal("0.00"):
            discount_pct = (discount_amount / subtotal) * Decimal("100.00")
            if discount_pct > settings.billing_discount_senior_approval_threshold_percent:
                user_roles = {r.name for r in getattr(target_user, "roles", [])}
                user_perms = {p.code for p in getattr(target_user, "permissions", [])}
                is_senior = (
                    "Finance Manager" in user_roles
                    or "Facility Administrator" in user_roles
                    or "finance.configure" in user_perms
                )
                if not is_senior:
                    raise HTTPException(
                        403,
                        f"Invoice discount of {discount_pct:.1f}% exceeds senior threshold ({settings.billing_discount_senior_approval_threshold_percent:.1f}%). Must be approved by Finance Manager or issued as DRAFT.",
                    )
        return True

    def record_payment(self, data: PaymentIn, invoice_allocations: dict[UUID, Decimal] = None) -> Payment:
        ref = data.transaction_reference or generate_reference_code(
            self.db, self.facility_id, "PAYMENT"
        )
        pay_amount = money(data.amount)
        payment = Payment(
            facility_id=self.facility_id,
            payer_id=data.payer_id,
            client_id=data.client_id,
            amount=pay_amount,
            payment_method=data.payment_method,
            transaction_reference=ref,
            payment_date=data.payment_date,
            notes=data.notes,
            status="COMPLETED",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(payment)
        self.db.flush()
        self.event("billing.payment_received", payment)

        # Atomic GL Posting: Dr Cash / Bank / M-Pesa / Cr Accounts Receivable (1200)
        # Never swallow exceptions!
        ledger = FinanceLedgerService(self.db, self.request, self.actor)
        pay_acct_code = PAYMENT_ACCOUNT_BY_METHOD.get(data.payment_method.upper(), "1000")
        entry_dt = payment.payment_date.date() if hasattr(payment.payment_date, "date") else payment.payment_date
        ledger.post_journal(
            entry_date=entry_dt,
            reference=payment.transaction_reference or f"PAY-{str(payment.id)[:8]}",
            description=f"Payment received via {payment.payment_method}",
            source_module="BILLING_PAYMENT",
            source_id=str(payment.id),
            posting_type="PAYMENT",
            lines=[
                {"account_code": pay_acct_code, "debit": pay_amount, "credit": Decimal("0.00")},
                {"account_code": "1200", "debit": Decimal("0.00"), "credit": pay_amount},
            ],
        )

        if invoice_allocations:
            for inv_id, alloc_amount in invoice_allocations.items():
                self.allocate_payment(payment.id, inv_id, money(alloc_amount))

        return payment

    def allocate_payment(self, payment_id: UUID, invoice_id: UUID, amount: Decimal):
        alloc_amount = money(amount)
        allocation = PaymentAllocation(
            payment_id=payment_id,
            invoice_id=invoice_id,
            amount=alloc_amount,
            allocated_at=utcnow(),
            allocated_by=self.actor.id,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(allocation)
        self.db.flush()

        # Update invoice status using exact Decimal comparison
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            raw_sum = self.db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == invoice_id).scalar()
            total_allocated = money(raw_sum) if raw_sum is not None else Decimal("0.00")
            if total_allocated >= invoice.total_amount:
                invoice.status = "PAID"
            elif total_allocated > Decimal("0.00"):
                invoice.status = "PARTIAL"
            self.event("billing.invoice_status_updated", invoice)

    def get_invoice_balance(self, invoice_id: UUID) -> Decimal:
        """Calculate net remaining balance on invoice (total_amount - payments - credit_notes - write_offs)."""
        invoice = self.db.get(Invoice, invoice_id)
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        raw_allocs = self.db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == invoice.id).scalar()
        total_allocated = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")
        raw_cns = self.db.query(func.sum(CreditNote.amount)).filter(
            CreditNote.invoice_id == invoice.id,
            CreditNote.status.in_(("POSTED", "APPROVED")),
        ).scalar()
        total_credits = money(raw_cns) if raw_cns is not None else Decimal("0.00")
        raw_wos = self.db.query(func.sum(WriteOff.amount)).filter(
            WriteOff.invoice_id == invoice.id,
            WriteOff.status.in_(("POSTED", "APPROVED")),
        ).scalar()
        total_wos = money(raw_wos) if raw_wos is not None else Decimal("0.00")
        return max(Decimal("0.00"), invoice.total_amount - total_allocated - total_credits - total_wos)

    # --- Phase 26.5: Credit Note Workflow ---

    def create_credit_note(self, data: CreditNoteIn) -> CreditNote:
        invoice = self.db.get(Invoice, data.invoice_id)
        if not invoice or invoice.facility_id != self.facility_id:
            raise HTTPException(404, "Invoice not found")
        if invoice.status not in ("ISSUED", "PARTIAL", "PAID", "OVERDUE"):
            raise HTTPException(
                400,
                f"Credit notes can only be issued for finalized invoices (ISSUED, PARTIAL, PAID, OVERDUE). Invoice is in '{invoice.status}' status.",
            )

        credit_amount = money(data.amount)
        if credit_amount <= Decimal("0.00"):
            raise HTTPException(422, "Credit note amount must be greater than zero")

        # Check existing credit notes and allocations
        raw_cns = self.db.query(func.sum(CreditNote.amount)).filter(
            CreditNote.invoice_id == invoice.id,
            CreditNote.status.in_(("POSTED", "PENDING_APPROVAL", "APPROVED")),
        ).scalar()
        existing_cn_total = money(raw_cns) if raw_cns is not None else Decimal("0.00")
        max_credit = max(Decimal("0.00"), invoice.total_amount - existing_cn_total)

        if credit_amount > max_credit:
            raise HTTPException(
                400,
                f"Requested credit note of KES {credit_amount:,.2f} exceeds remaining credit limit of KES {max_credit:,.2f} on invoice {invoice.invoice_number}.",
            )

        credit_number = generate_reference_code(self.db, self.facility_id, "CREDIT_NOTE")
        cn = CreditNote(
            facility_id=self.facility_id,
            invoice_id=invoice.id,
            credit_number=credit_number,
            amount=credit_amount,
            reason_code=data.reason_code,
            reason=data.reason,
            status="PENDING_APPROVAL",
            issued_at=utcnow(),
            issued_by=self.actor.id,
            requested_by=self.actor.id,
            requested_at=utcnow(),
            approval_notes="",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(cn)
        self.db.flush()
        self.event("billing.credit_note_requested", cn)
        return cn

    def approve_credit_note(self, credit_note_id: UUID, notes: str = "") -> CreditNote:
        cn = self.db.get(CreditNote, credit_note_id)
        if not cn or cn.facility_id != self.facility_id:
            raise HTTPException(404, "Credit note not found")
        if cn.status != "PENDING_APPROVAL":
            raise HTTPException(400, f"Cannot approve credit note in '{cn.status}' status. Only 'PENDING_APPROVAL' credit notes can be approved.")

        # Four-Eyes Maker-Checker rule
        if cn.requested_by == self.actor.id or cn.created_by == self.actor.id:
            raise HTTPException(
                403,
                "Segregation of duties violation: Creators/requesters cannot approve their own credit notes.",
            )

        invoice = self.db.get(Invoice, cn.invoice_id)
        if not invoice:
            raise HTTPException(404, "Associated invoice not found")

        # Atomic GL posting: Dr Patient Service Revenue (4000) / Cr Accounts Receivable (1200)
        ledger = FinanceLedgerService(self.db, self.request, self.actor)
        entry = ledger.post_journal(
            entry_date=utcnow().date(),
            reference=cn.credit_number,
            description=f"Credit Note {cn.credit_number} for Invoice {invoice.invoice_number}: {cn.reason}",
            source_module="CREDIT_NOTE",
            source_id=str(cn.id),
            posting_type="CREDIT_NOTE",
            lines=[
                {"account_code": "4000", "debit": cn.amount, "credit": Decimal("0.00")},
                {"account_code": "1200", "debit": Decimal("0.00"), "credit": cn.amount},
            ],
        )

        cn.journal_id = entry.id
        cn.approved_by = self.actor.id
        cn.approved_at = utcnow()
        cn.approval_notes = notes
        cn.status = "POSTED"
        cn.updated_by = self.actor.id

        # Update invoice status without mutating original issued total_amount
        raw_allocs = self.db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == invoice.id).scalar()
        total_allocated = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")
        raw_cns = self.db.query(func.sum(CreditNote.amount)).filter(
            CreditNote.invoice_id == invoice.id,
            CreditNote.status.in_(("POSTED", "APPROVED")),
        ).scalar()
        total_credits = money(raw_cns) if raw_cns is not None else Decimal("0.00")
        if total_allocated + total_credits >= invoice.total_amount:
            invoice.status = "PAID"
        elif total_allocated + total_credits > Decimal("0.00"):
            invoice.status = "PARTIAL"

        self.db.flush()
        self.event("billing.credit_note_approved", cn)
        return cn

    def reject_credit_note(self, credit_note_id: UUID, notes: str = "") -> CreditNote:
        cn = self.db.get(CreditNote, credit_note_id)
        if not cn or cn.facility_id != self.facility_id:
            raise HTTPException(404, "Credit note not found")
        if cn.status != "PENDING_APPROVAL":
            raise HTTPException(400, f"Cannot reject credit note in '{cn.status}' status. Only 'PENDING_APPROVAL' credit notes can be rejected.")

        if cn.requested_by == self.actor.id or cn.created_by == self.actor.id:
            raise HTTPException(
                403,
                "Segregation of duties violation: Requesters cannot reject their own credit notes.",
            )

        cn.status = "REJECTED"
        cn.approved_by = self.actor.id
        cn.approved_at = utcnow()
        cn.approval_notes = notes
        cn.updated_by = self.actor.id
        self.db.flush()
        self.event("billing.credit_note_rejected", cn)
        return cn

    # --- Phase 26.5: Write-Off Workflow ---

    def create_writeoff(self, data: WriteOffIn) -> WriteOff:
        invoice = self.db.get(Invoice, data.invoice_id)
        if not invoice or invoice.facility_id != self.facility_id:
            raise HTTPException(404, "Invoice not found")
        if invoice.status not in ("ISSUED", "PARTIAL", "OVERDUE"):
            raise HTTPException(
                400,
                f"Cannot request write-off for invoice in '{invoice.status}' status. Only unpaid/partially paid issued invoices can be written off.",
            )

        wo_amount = money(data.amount)
        if wo_amount <= Decimal("0.00"):
            raise HTTPException(422, "Write-off amount must be greater than zero")

        raw_allocs = self.db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == invoice.id).scalar()
        allocs = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")
        outstanding = max(Decimal("0.00"), invoice.total_amount - allocs)

        if wo_amount > outstanding:
            raise HTTPException(
                400,
                f"Write-off amount of KES {wo_amount:,.2f} exceeds outstanding invoice balance of KES {outstanding:,.2f}.",
            )

        ref_code = generate_reference_code(self.db, self.facility_id, "WRITE_OFF")
        wo = WriteOff(
            facility_id=self.facility_id,
            invoice_id=invoice.id,
            reference_code=ref_code,
            amount=wo_amount,
            reason=data.reason,
            status="PENDING_APPROVAL",
            requested_by=self.actor.id,
            requested_at=utcnow(),
            approved_by=None,
            approved_at=None,
            written_off_at=None,
            approval_notes="",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(wo)
        self.db.flush()
        self.event("billing.writeoff_requested", wo)
        # Note: Invoice is NOT marked written off until independent supervisor approval!
        return wo

    def approve_writeoff(self, writeoff_id: UUID, notes: str = "") -> WriteOff:
        wo = self.db.get(WriteOff, writeoff_id)
        if not wo or wo.facility_id != self.facility_id:
            raise HTTPException(404, "Write-off record not found")
        if wo.status != "PENDING_APPROVAL":
            raise HTTPException(400, f"Cannot approve write-off in '{wo.status}' status. Only 'PENDING_APPROVAL' records can be approved.")

        # Four-Eyes Segregation of Duties
        if wo.requested_by == self.actor.id or wo.created_by == self.actor.id:
            raise HTTPException(
                403,
                "Segregation of duties violation: Requesters cannot approve their own debt write-offs.",
            )

        # Senior approval threshold check for write-offs > KES 50,000
        settings = get_settings()
        if wo.amount > settings.finance_expense_senior_approval_threshold:
            user_roles = {r.name for r in getattr(self.actor, "roles", [])}
            user_perms = {p.code for p in getattr(self.actor, "permissions", [])}
            is_senior = (
                "Finance Manager" in user_roles
                or "Facility Administrator" in user_roles
                or "finance.configure" in user_perms
            )
            if not is_senior:
                raise HTTPException(
                    403,
                    f"Debt write-offs exceeding KSh {settings.finance_expense_senior_approval_threshold:,.2f} require senior authorization (Finance Manager or Facility Administrator).",
                )

        invoice = self.db.get(Invoice, wo.invoice_id)
        if not invoice:
            raise HTTPException(404, "Associated invoice not found")

        # Atomic GL posting: Dr Bad Debt Expense (6000) / Cr Accounts Receivable (1200)
        ledger = FinanceLedgerService(self.db, self.request, self.actor)
        entry = ledger.post_journal(
            entry_date=utcnow().date(),
            reference=wo.reference_code or f"WO-{str(wo.id)[:8]}",
            description=f"Bad debt write-off for invoice {invoice.invoice_number}: {wo.reason}",
            source_module="BILLING_WRITEOFF",
            source_id=str(wo.id),
            posting_type="WRITEOFF",
            lines=[
                {"account_code": "6000", "debit": wo.amount, "credit": Decimal("0.00")},
                {"account_code": "1200", "debit": Decimal("0.00"), "credit": wo.amount},
            ],
        )

        wo.journal_id = entry.id
        wo.approved_by = self.actor.id
        wo.approved_at = utcnow()
        wo.written_off_at = utcnow()
        wo.approval_notes = notes
        wo.status = "POSTED"
        wo.updated_by = self.actor.id

        # Update invoice status: if full remaining balance is written off, mark WRITTEN_OFF
        raw_allocs = self.db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == invoice.id).scalar()
        allocs = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")
        if allocs + wo.amount >= invoice.total_amount:
            invoice.status = "WRITTEN_OFF"

        self.db.flush()
        self.event("billing.writeoff_approved", wo)
        return wo

    def reject_writeoff(self, writeoff_id: UUID, notes: str = "") -> WriteOff:
        wo = self.db.get(WriteOff, writeoff_id)
        if not wo or wo.facility_id != self.facility_id:
            raise HTTPException(404, "Write-off record not found")
        if wo.status != "PENDING_APPROVAL":
            raise HTTPException(400, f"Cannot reject write-off in '{wo.status}' status. Only 'PENDING_APPROVAL' records can be rejected.")

        if wo.requested_by == self.actor.id or wo.created_by == self.actor.id:
            raise HTTPException(
                403,
                "Segregation of duties violation: Requesters cannot reject their own write-offs.",
            )

        wo.status = "REJECTED"
        wo.approved_by = self.actor.id
        wo.approved_at = utcnow()
        wo.approval_notes = notes
        wo.updated_by = self.actor.id
        self.db.flush()
        self.event("billing.writeoff_rejected", wo)
        return wo
