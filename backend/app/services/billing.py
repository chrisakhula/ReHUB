"""Billing service: Invoicing, payments, credit notes, write-offs, and atomic GL posting."""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

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
    ProgrammePackage,
    CreditNote,
    Refund,
    Adjustment,
    WriteOff,
    MpesaTransaction,
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
)
from app.models.clients import Client, Admission
from app.schemas.billing import (
    InvoiceIn,
    PaymentIn,
    CreditNoteIn,
    WriteOffIn,
    SponsorIn,
    FinancialAssessmentIn,
    FinancialQuotationIn,
    FinancialAgreementIn,
    FinancialAgreementReviseIn,
    PackageServiceInclusionIn,
    RecurringBillingScheduleIn,
    InvoicePayerAllocationIn,
    PaymentPlanIn,
    RefundRequestIn,
    ResidentFundDepositIn,
    ResidentFundWithdrawIn,
    DischargeClearanceReviewIn,
    ClientFinancialAccountSummary,
    SponsorStatementSummary,
    SponsorStatementClientRow,
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

    # =========================================================================
    # Phase 26.6 - Sprint A: Pre-Admission Financial Assessment & Quotations
    # =========================================================================

    def create_financial_assessment(self, data: FinancialAssessmentIn) -> FinancialAssessment:
        ref_code = generate_reference_code(self.db, self.facility_id, "FINANCIAL_ASSESSMENT")
        client = self.db.get(Client, data.client_id)
        if not client or client.facility_id != self.facility_id:
            raise HTTPException(404, "Client not found in facility")

        assessment = FinancialAssessment(
            facility_id=self.facility_id,
            client_id=data.client_id,
            reference_code=ref_code,
            proposed_programme=data.proposed_programme,
            expected_duration_days=data.expected_duration_days,
            expected_admission_date=data.expected_admission_date,
            primary_payer_type=data.primary_payer_type,
            primary_payer_name=data.primary_payer_name,
            secondary_payer_type=data.secondary_payer_type,
            secondary_payer_name=data.secondary_payer_name,
            sponsor_id=data.sponsor_id,
            estimated_programme_cost=data.estimated_programme_cost,
            deposit_required=data.deposit_required,
            credit_terms=data.credit_terms,
            installment_preference=data.installment_preference,
            discount_eligibility=data.discount_eligibility,
            authorization_limit=data.authorization_limit,
            financial_notes=data.financial_notes,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(assessment)
        self.db.flush()
        self.event("billing.financial_assessment_created", assessment)
        return assessment

    def get_financial_assessment(self, assessment_id: UUID) -> FinancialAssessment:
        row = self.db.get(FinancialAssessment, assessment_id)
        if not row or row.facility_id != self.facility_id:
            raise HTTPException(404, "Financial assessment not found")
        return row

    def list_financial_assessments(self, client_id: Optional[UUID] = None) -> list[FinancialAssessment]:
        q = self.db.query(FinancialAssessment).filter(FinancialAssessment.facility_id == self.facility_id)
        if client_id:
            q = q.filter(FinancialAssessment.client_id == client_id)
        return q.order_by(FinancialAssessment.created_at.desc()).all()

    def create_quotation(self, data: FinancialQuotationIn) -> FinancialQuotation:
        ref_code = generate_reference_code(self.db, self.facility_id, "ESTIMATE")
        client = self.db.get(Client, data.client_id)
        if not client or client.facility_id != self.facility_id:
            raise HTTPException(404, "Client not found in facility")

        subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")
        total_tax = Decimal("0.00")

        items_to_add = []
        for it in data.items:
            line_gross = money(it.quantity * it.unit_price)
            line_disc = money(it.discount)
            line_net = max(Decimal("0.00"), line_gross - line_disc)
            line_tax = money(line_net * (it.tax_rate / Decimal("100.00")))
            line_total = line_net + line_tax

            subtotal += line_gross
            total_discount += line_disc
            total_tax += line_tax

            items_to_add.append((it, line_total))

        total_amount = max(Decimal("0.00"), subtotal - total_discount + total_tax)

        quotation = FinancialQuotation(
            facility_id=self.facility_id,
            client_id=data.client_id,
            assessment_id=data.assessment_id,
            reference_code=ref_code,
            status="DRAFT",
            programme_name=data.programme_name,
            duration_days=data.duration_days,
            subtotal=subtotal,
            discount_amount=total_discount,
            tax_amount=total_tax,
            total_amount=total_amount,
            deposit_required=data.deposit_required,
            valid_until=data.valid_until,
            terms_and_conditions=data.terms_and_conditions,
            notes=data.notes,
            created_by=self.actor.id,
        )
        self.db.add(quotation)
        self.db.flush()

        for it, line_total in items_to_add:
            item_row = FinancialQuotationItem(
                quotation_id=quotation.id,
                service_id=it.service_id,
                package_id=it.package_id,
                category=it.category,
                description=it.description,
                quantity=it.quantity,
                unit_price=it.unit_price,
                discount=it.discount,
                tax_rate=it.tax_rate,
                total_price=line_total,
            )
            self.db.add(item_row)

        self.db.flush()
        self.event("billing.quotation_created", quotation)
        return quotation

    def get_quotation(self, quotation_id: UUID) -> FinancialQuotation:
        row = self.db.get(FinancialQuotation, quotation_id)
        if not row or row.facility_id != self.facility_id:
            raise HTTPException(404, "Quotation not found")
        return row

    def issue_quotation(self, quotation_id: UUID) -> FinancialQuotation:
        quotation = self.get_quotation(quotation_id)
        if quotation.status != "DRAFT":
            raise HTTPException(400, f"Cannot issue quotation with status '{quotation.status}'")
        quotation.status = "ISSUED"
        self.db.flush()
        self.event("billing.quotation_issued", quotation)
        return quotation

    def accept_quotation(self, quotation_id: UUID, accepted_by: str) -> FinancialQuotation:
        quotation = self.get_quotation(quotation_id)
        if quotation.status not in ("DRAFT", "ISSUED"):
            raise HTTPException(400, f"Cannot accept quotation in '{quotation.status}' status")
        quotation.status = "ACCEPTED"
        quotation.accepted_by = accepted_by
        quotation.accepted_at = utcnow()
        self.db.flush()
        self.event("billing.quotation_accepted", quotation)
        return quotation

    def convert_quotation_to_agreement(self, quotation_id: UUID, admission_id: Optional[UUID] = None) -> FinancialAgreement:
        quotation = self.get_quotation(quotation_id)
        if quotation.status != "ACCEPTED":
            raise HTTPException(400, "Only accepted quotations can be converted to financial agreements")
        if quotation.converted_agreement_id:
            existing = self.db.get(FinancialAgreement, quotation.converted_agreement_id)
            if existing:
                return existing

        fag_code = generate_reference_code(self.db, self.facility_id, "FINANCIAL_AGREEMENT")
        agreement = FinancialAgreement(
            facility_id=self.facility_id,
            client_id=quotation.client_id,
            admission_id=admission_id,
            quotation_id=quotation.id,
            reference_code=fag_code,
            version=1,
            programme_name=quotation.programme_name,
            agreed_price=quotation.total_amount,
            deposit_amount=quotation.deposit_required,
            deposit_paid=Decimal("0.00"),
            installment_terms="Standard admission payment terms",
            credit_terms="30 days",
            inclusions="Standard package inclusions per quotation",
            exclusions="External laboratory/specialist consultations",
            refund_terms="Institutional refund policy applies",
            approved_discount=quotation.discount_amount,
            effective_date=utcnow().date(),
            status="PENDING_ACCEPTANCE",
            accepted_by_name=quotation.accepted_by,
            accepted_at=quotation.accepted_at,
            notes=f"Converted from estimate {quotation.reference_code}",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(agreement)
        self.db.flush()

        quotation.status = "CONVERTED"
        quotation.converted_agreement_id = agreement.id
        self.db.flush()
        self.event("billing.quotation_converted", agreement)
        return agreement

    def create_financial_agreement(self, data: FinancialAgreementIn) -> FinancialAgreement:
        fag_code = generate_reference_code(self.db, self.facility_id, "FINANCIAL_AGREEMENT")
        agreement = FinancialAgreement(
            facility_id=self.facility_id,
            client_id=data.client_id,
            admission_id=data.admission_id,
            quotation_id=data.quotation_id,
            reference_code=fag_code,
            version=1,
            programme_name=data.programme_name,
            agreed_price=data.agreed_price,
            deposit_amount=data.deposit_amount,
            deposit_paid=Decimal("0.00"),
            installment_terms=data.installment_terms,
            credit_terms=data.credit_terms,
            inclusions=data.inclusions,
            exclusions=data.exclusions,
            refund_terms=data.refund_terms,
            approved_discount=data.approved_discount,
            effective_date=data.effective_date,
            status="PENDING_ACCEPTANCE",
            notes=data.notes,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(agreement)
        self.db.flush()
        self.event("billing.agreement_created", agreement)
        return agreement

    def revise_financial_agreement(self, agreement_id: UUID, data: FinancialAgreementReviseIn) -> FinancialAgreement:
        parent = self.db.get(FinancialAgreement, agreement_id)
        if not parent or parent.facility_id != self.facility_id:
            raise HTTPException(404, "Financial agreement not found")

        parent.status = "REVISED"
        parent.updated_by = self.actor.id

        new_agreement = FinancialAgreement(
            facility_id=self.facility_id,
            client_id=parent.client_id,
            admission_id=parent.admission_id,
            quotation_id=parent.quotation_id,
            reference_code=parent.reference_code,
            version=parent.version + 1,
            parent_agreement_id=parent.id,
            revision_reason=data.revision_reason,
            programme_name=parent.programme_name,
            agreed_price=data.agreed_price,
            deposit_amount=data.deposit_amount,
            deposit_paid=parent.deposit_paid,
            installment_terms=data.installment_terms or parent.installment_terms,
            credit_terms=parent.credit_terms,
            inclusions=data.inclusions or parent.inclusions,
            exclusions=data.exclusions or parent.exclusions,
            refund_terms=parent.refund_terms,
            approved_discount=parent.approved_discount,
            effective_date=utcnow().date(),
            status="PENDING_ACCEPTANCE",
            notes=f"Revision of version {parent.version}: {data.revision_reason}",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(new_agreement)
        self.db.flush()
        self.event("billing.agreement_revised", new_agreement)
        return new_agreement

    def approve_financial_agreement(self, agreement_id: UUID, notes: str = "") -> FinancialAgreement:
        agreement = self.db.get(FinancialAgreement, agreement_id)
        if not agreement or agreement.facility_id != self.facility_id:
            raise HTTPException(404, "Financial agreement not found")
        if agreement.created_by == self.actor.id:
            raise HTTPException(403, "Segregation of duties violation: Agreement creator cannot approve their own agreement.")
        if agreement.status not in ("DRAFT", "PENDING_ACCEPTANCE"):
            raise HTTPException(400, f"Cannot approve agreement with status '{agreement.status}'")

        agreement.status = "ACTIVE"
        agreement.authorized_by_id = self.actor.id
        agreement.authorized_at = utcnow()
        if notes:
            agreement.notes = f"{agreement.notes} | Approval: {notes}".strip(" |")
        agreement.updated_by = self.actor.id
        self.db.flush()
        self.event("billing.agreement_approved", agreement)
        return agreement

    # =========================================================================
    # Phase 26.6 - Sprint B: Package Consumption & Recurring Billing
    # =========================================================================

    def configure_package_inclusion(self, package_id: UUID, data: PackageServiceInclusionIn) -> PackageServiceInclusion:
        pkg = self.db.get(ProgrammePackage, package_id)
        if not pkg:
            raise HTTPException(404, "Programme package not found")
        inc = PackageServiceInclusion(
            package_id=package_id,
            service_id=data.service_id,
            category=data.category,
            classification=data.classification,
            allowed_quantity=data.allowed_quantity,
            discount_percentage=data.discount_percentage,
        )
        self.db.add(inc)
        self.db.flush()
        return inc

    def initialize_admission_package_consumption(self, admission_id: UUID, package_id: UUID):
        inclusions = self.db.query(PackageServiceInclusion).filter(PackageServiceInclusion.package_id == package_id).all()
        for inc in inclusions:
            existing = self.db.query(PackageConsumption).filter(
                PackageConsumption.admission_id == admission_id,
                PackageConsumption.category == inc.category,
            ).first()
            if not existing:
                consumption = PackageConsumption(
                    facility_id=self.facility_id,
                    admission_id=admission_id,
                    package_id=package_id,
                    service_id=inc.service_id,
                    category=inc.category,
                    quantity_allowed=inc.allowed_quantity,
                    quantity_used=0,
                    quantity_remaining=inc.allowed_quantity,
                )
                self.db.add(consumption)
        self.db.flush()

    def record_service_charge(
        self,
        admission_id: UUID,
        service_id: Optional[UUID],
        category: str,
        quantity: Decimal,
        unit_price: Decimal,
        description: str,
        source_module: str,
        source_id: str,
        charge_type: str = "DIRECT",
    ) -> dict:
        # Check duplicate charge
        existing = self.db.query(InvoiceItem).filter(
            InvoiceItem.source_module == source_module,
            InvoiceItem.source_id == source_id,
        ).first()
        if existing:
            return {
                "status": "DUPLICATE_PREVENTED",
                "invoice_item_id": str(existing.id),
                "billed": False,
                "reason": f"Already billed under item {existing.id}",
            }

        # Check package consumption
        consumption = self.db.query(PackageConsumption).filter(
            PackageConsumption.facility_id == self.facility_id,
            PackageConsumption.admission_id == admission_id,
            or_(
                PackageConsumption.service_id == service_id,
                PackageConsumption.category == category,
            ),
        ).first()

        int_qty = int(quantity)
        if consumption and consumption.quantity_remaining >= int_qty:
            consumption.quantity_used += int_qty
            consumption.quantity_remaining -= int_qty
            self.db.flush()
            return {
                "status": "PACKAGE_COVERED",
                "billed": False,
                "consumed_quantity": int_qty,
                "remaining_quantity": consumption.quantity_remaining,
            }

        admission = self.db.get(Admission, admission_id)
        if not admission:
            raise HTTPException(404, "Admission not found")

        invoice = self.db.query(Invoice).filter(
            Invoice.facility_id == self.facility_id,
            Invoice.admission_id == admission_id,
            Invoice.status.in_(["DRAFT", "ISSUED", "PARTIAL"]),
        ).order_by(Invoice.created_at.desc()).first()

        if not invoice:
            inv_num = generate_reference_code(self.db, self.facility_id, "INVOICE")
            invoice = Invoice(
                facility_id=self.facility_id,
                client_id=admission.client_id,
                admission_id=admission_id,
                invoice_number=inv_num,
                issue_date=utcnow().date(),
                due_date=utcnow().date(),
                status="ISSUED",
                notes=f"Auto-generated charges for admission {admission.admission_number}",
                created_by=self.actor.id,
                updated_by=self.actor.id,
            )
            self.db.add(invoice)
            self.db.flush()

        line_total = money(quantity * unit_price)
        item = InvoiceItem(
            invoice_id=invoice.id,
            service_id=service_id,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            discount=Decimal("0.00"),
            tax_rate=Decimal("0.00"),
            total_price=line_total,
            source_module=source_module,
            source_id=source_id,
            charge_type=charge_type,
        )
        self.db.add(item)
        invoice.total_amount += line_total
        invoice.subtotal += line_total
        self.db.flush()
        return {
            "status": "BILLED",
            "billed": True,
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "amount": line_total,
        }

    def record_package_consumption(
        self,
        admission_id: UUID,
        package_id: UUID,
        category: str,
        quantity_to_consume: int,
        unit_price: Decimal = Decimal("0.00"),
    ) -> dict:
        self.initialize_admission_package_consumption(admission_id, package_id)
        consumption = self.db.query(PackageConsumption).filter(
            PackageConsumption.facility_id == self.facility_id,
            PackageConsumption.admission_id == admission_id,
            PackageConsumption.package_id == package_id,
            PackageConsumption.category == category,
        ).first()

        if not consumption:
            return {
                "status": "NOT_INCLUDED",
                "consumed_from_package": 0,
                "extra_billed_quantity": quantity_to_consume,
                "extra_billable_amount": money(Decimal(quantity_to_consume) * unit_price),
                "quantity_remaining": 0,
            }

        if consumption.quantity_remaining >= quantity_to_consume:
            consumption.quantity_used += quantity_to_consume
            consumption.quantity_remaining -= quantity_to_consume
            self.db.flush()
            return {
                "status": "COVERED",
                "consumed_from_package": quantity_to_consume,
                "extra_billed_quantity": 0,
                "extra_billable_amount": Decimal("0.00"),
                "quantity_remaining": consumption.quantity_remaining,
            }
        else:
            covered = consumption.quantity_remaining
            extra = quantity_to_consume - covered
            consumption.quantity_used += covered
            consumption.quantity_remaining = 0
            extra_amount = money(Decimal(extra) * unit_price)
            self.db.flush()
            return {
                "status": "QUOTA_EXCEEDED",
                "consumed_from_package": covered,
                "extra_billed_quantity": extra,
                "extra_billable_amount": extra_amount,
                "quantity_remaining": 0,
            }

    def generate_service_charge(
        self,
        admission_id: UUID,
        source_module: str,
        source_id: str,
        charge_type: str,
        description: str,
        amount: Decimal,
        quantity: Decimal = Decimal("1.00"),
    ) -> InvoiceItem:
        existing = self.db.query(InvoiceItem).filter(
            InvoiceItem.source_module == source_module,
            InvoiceItem.source_id == source_id,
        ).first()
        if existing:
            raise HTTPException(400, f"Duplicate charge: Source '{source_module}:{source_id}' already billed.")

        admission = self.db.get(Admission, admission_id)
        if not admission:
            raise HTTPException(404, "Admission not found")

        invoice = self.db.query(Invoice).filter(
            Invoice.facility_id == self.facility_id,
            Invoice.admission_id == admission_id,
            Invoice.status.in_(["DRAFT", "ISSUED", "PARTIAL"]),
        ).order_by(Invoice.created_at.desc()).first()

        if not invoice:
            inv_num = generate_reference_code(self.db, self.facility_id, "INVOICE")
            invoice = Invoice(
                facility_id=self.facility_id,
                client_id=admission.client_id,
                admission_id=admission_id,
                invoice_number=inv_num,
                issue_date=utcnow().date(),
                due_date=utcnow().date(),
                status="ISSUED",
                notes=f"Auto-generated charges for admission {admission.admission_number}",
                created_by=self.actor.id,
                updated_by=self.actor.id,
            )
            self.db.add(invoice)
            self.db.flush()

        line_total = money(amount)
        unit_price = money(amount / quantity) if quantity > 0 else line_total
        item = InvoiceItem(
            invoice_id=invoice.id,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            discount=Decimal("0.00"),
            tax_rate=Decimal("0.00"),
            total_price=line_total,
            source_module=source_module,
            source_id=source_id,
            charge_type=charge_type,
        )
        self.db.add(item)
        invoice.total_amount += line_total
        invoice.subtotal += line_total
        self.db.flush()
        return item

    # Convenience aliases for Phase 26.6
    create_financial_quotation = create_quotation
    issue_financial_quotation = issue_quotation
    accept_financial_quotation = accept_quotation
    create_package_inclusion = configure_package_inclusion

    def create_recurring_schedule(self, data: RecurringBillingScheduleIn) -> RecurringBillingSchedule:
        admission = self.db.get(Admission, data.admission_id)
        if not admission or admission.facility_id != self.facility_id:
            raise HTTPException(404, "Admission not found")
        if admission.status in ["DISCHARGED", "CLOSED"]:
            raise HTTPException(400, "Cannot create recurring billing schedule for a discharged or closed admission")

        sched = RecurringBillingSchedule(
            facility_id=self.facility_id,
            admission_id=data.admission_id,
            frequency=data.frequency,
            service_id=data.service_id,
            description=data.description,
            amount=data.amount,
            next_run_date=data.next_run_date,
            is_active=True,
            source_module="RECURRING",
        )
        self.db.add(sched)
        self.db.flush()
        self.event("billing.recurring_schedule_created", sched)
        return sched

    def process_due_recurring_schedules(self, target_date: Optional[date] = None) -> list[InvoiceItem]:
        if not target_date:
            target_date = utcnow().date()

        schedules = self.db.query(RecurringBillingSchedule).filter(
            RecurringBillingSchedule.facility_id == self.facility_id,
            RecurringBillingSchedule.is_active == True,
            RecurringBillingSchedule.next_run_date <= target_date,
        ).all()

        generated_items = []
        for sched in schedules:
            adm = self.db.get(Admission, sched.admission_id)
            if not adm or adm.status in ["DISCHARGED", "CLOSED"]:
                sched.is_active = False
                continue

            # Idempotency check: check if already billed for this schedule and target date
            source_id = f"{sched.id}:{target_date.isoformat()}"
            existing = self.db.query(InvoiceItem).filter(
                InvoiceItem.source_module == "RECURRING",
                InvoiceItem.source_id == source_id,
            ).first()
            if existing:
                continue

            invoice = self.db.query(Invoice).filter(
                Invoice.facility_id == self.facility_id,
                Invoice.admission_id == sched.admission_id,
                Invoice.status.in_(["DRAFT", "ISSUED", "PARTIAL"]),
            ).order_by(Invoice.created_at.desc()).first()

            if not invoice:
                inv_num = generate_reference_code(self.db, self.facility_id, "INVOICE")
                invoice = Invoice(
                    facility_id=self.facility_id,
                    client_id=adm.client_id,
                    admission_id=adm.id,
                    invoice_number=inv_num,
                    issue_date=target_date,
                    due_date=target_date,
                    status="ISSUED",
                    notes=f"Recurring charges for admission {adm.admission_number}",
                    created_by=self.actor.id,
                    updated_by=self.actor.id,
                )
                self.db.add(invoice)
                self.db.flush()

            line_total = money(sched.amount)
            item = InvoiceItem(
                invoice_id=invoice.id,
                service_id=sched.service_id,
                description=f"{sched.description} ({target_date.isoformat()})",
                quantity=Decimal("1.00"),
                unit_price=line_total,
                discount=Decimal("0.00"),
                tax_rate=Decimal("0.00"),
                total_price=line_total,
                source_module="RECURRING",
                source_id=source_id,
                charge_type="RECURRING",
            )
            self.db.add(item)
            invoice.total_amount += line_total
            invoice.subtotal += line_total

            sched.last_run_date = target_date
            if sched.frequency == "DAILY":
                sched.next_run_date = target_date + timedelta(days=1)
            elif sched.frequency == "WEEKLY":
                sched.next_run_date = target_date + timedelta(days=7)
            elif sched.frequency == "MONTHLY":
                sched.next_run_date = target_date + timedelta(days=30)
            else:
                sched.next_run_date = target_date + timedelta(days=1)

            generated_items.append(item)

        self.db.flush()
        return generated_items


    # =========================================================================
    # Phase 26.6 - Sprint C: Sponsors & Split Payer Allocation
    # =========================================================================

    def create_sponsor(self, data: SponsorIn) -> Sponsor:
        ref_code = generate_reference_code(self.db, self.facility_id, "SPONSOR")
        sponsor = Sponsor(
            facility_id=self.facility_id,
            reference_code=ref_code,
            name=data.name,
            sponsor_type=data.sponsor_type,
            contact_person=data.contact_person,
            email=data.email,
            phone=data.phone,
            billing_address=data.billing_address,
            credit_limit=data.credit_limit,
            balance=Decimal("0.00"),
        )
        self.db.add(sponsor)
        self.db.flush()
        self.event("billing.sponsor_created", sponsor)
        return sponsor

    def list_sponsors(self) -> list[Sponsor]:
        return self.db.query(Sponsor).filter(
            Sponsor.facility_id == self.facility_id,
            Sponsor.is_active == True,
        ).order_by(Sponsor.name.asc()).all()

    def allocate_invoice_payers(self, invoice_id: UUID, allocations: list[InvoicePayerAllocationIn]) -> list[InvoicePayerAllocation]:
        invoice = self.db.get(Invoice, invoice_id)
        if not invoice or invoice.facility_id != self.facility_id:
            raise HTTPException(404, "Invoice not found")

        total_pct = Decimal("0.00")
        total_amt = Decimal("0.00")
        for a in allocations:
            if a.allocation_type == "PERCENTAGE":
                total_pct += a.percentage
            total_amt += a.allocated_amount

        if total_pct > Decimal("100.00"):
            raise HTTPException(400, f"Total percentage allocation exceeds 100%: {total_pct}%")
        if total_amt > invoice.total_amount:
            raise HTTPException(400, f"Total allocated amount (KES {total_amt}) exceeds invoice total (KES {invoice.total_amount})")

        self.db.query(InvoicePayerAllocation).filter(InvoicePayerAllocation.invoice_id == invoice.id).delete()
        created = []
        for a in allocations:
            row = InvoicePayerAllocation(
                invoice_id=invoice.id,
                payer_id=a.payer_id,
                sponsor_id=a.sponsor_id,
                allocation_type=a.allocation_type,
                percentage=a.percentage,
                allocated_amount=a.allocated_amount,
                paid_amount=Decimal("0.00"),
                responsibility_description=a.responsibility_description,
                status="PENDING",
            )
            self.db.add(row)
            created.append(row)
        self.db.flush()
        self.event("billing.invoice_payers_allocated", invoice)
        return created

    set_invoice_payer_allocations = allocate_invoice_payers

    # =========================================================================
    # Phase 26.6 - Sprint D: Payment Plans, Refunds & Resident Funds
    # =========================================================================

    def create_payment_plan(self, data: PaymentPlanIn) -> PaymentPlan:
        ref_code = generate_reference_code(self.db, self.facility_id, "PAYMENT_PLAN")
        plan = PaymentPlan(
            facility_id=self.facility_id,
            client_id=data.client_id,
            admission_id=data.admission_id,
            invoice_id=data.invoice_id,
            reference_code=ref_code,
            total_amount=data.total_amount,
            number_of_installments=data.number_of_installments,
            status="DRAFT",
            notes=data.notes,
            created_by=self.actor.id,
        )
        self.db.add(plan)
        self.db.flush()

        for inst in data.installments:
            installment_row = PaymentPlanInstallment(
                plan_id=plan.id,
                installment_number=inst.installment_number,
                due_date=inst.due_date,
                amount=inst.amount,
                paid_amount=Decimal("0.00"),
                status="PENDING",
            )
            self.db.add(installment_row)

        self.db.flush()
        self.event("billing.payment_plan_created", plan)
        return plan

    def approve_payment_plan(self, plan_id: UUID) -> PaymentPlan:
        plan = self.db.get(PaymentPlan, plan_id)
        if not plan or plan.facility_id != self.facility_id:
            raise HTTPException(404, "Payment plan not found")
        if plan.created_by == self.actor.id:
            raise HTTPException(403, "Segregation of duties violation: Creator cannot approve their own payment plan.")

        plan.status = "ACTIVE"
        plan.approved_by = self.actor.id
        self.db.flush()
        self.event("billing.payment_plan_approved", plan)
        return plan

    def request_refund(self, data: RefundRequestIn) -> Refund:
        ref_code = generate_reference_code(self.db, self.facility_id, "REFUND")
        refund = Refund(
            facility_id=self.facility_id,
            reference_code=ref_code,
            client_id=data.client_id,
            payment_id=data.payment_id,
            amount=data.amount,
            reason=data.reason,
            source_type=data.source_type,
            refund_method=data.refund_method,
            transaction_reference=data.transaction_reference,
            status="PENDING_APPROVAL",
            requested_by=self.actor.id,
            requested_at=utcnow(),
        )
        self.db.add(refund)
        self.db.flush()
        self.event("billing.refund_requested", refund)
        return refund

    def approve_refund(self, refund_id: UUID, notes: str = "") -> Refund:
        refund = self.db.get(Refund, refund_id)
        if not refund or refund.facility_id != self.facility_id:
            raise HTTPException(404, "Refund not found")
        if refund.requested_by == self.actor.id or refund.created_by == self.actor.id:
            raise HTTPException(403, "Segregation of duties violation: Refund requester cannot approve their own refund.")
        if refund.status != "PENDING_APPROVAL":
            raise HTTPException(400, f"Cannot approve refund with status '{refund.status}'")

        debit_acct = "2200" if refund.source_type == "CLIENT_DEPOSIT" else "4000"
        credit_acct = PAYMENT_ACCOUNT_BY_METHOD.get(refund.refund_method.upper(), "1030")

        ledger = FinanceLedgerService(self.db, self.request, self.actor)
        entry = ledger.post_journal(
            entry_date=utcnow().date(),
            reference=refund.reference_code or f"RF-{str(refund.id)[:8]}",
            description=f"Approved client refund ({refund.source_type}): {refund.reason}",
            source_module="BILLING_REFUND",
            source_id=str(refund.id),
            posting_type="REFUND",
            lines=[
                {"account_code": debit_acct, "debit": refund.amount, "credit": Decimal("0.00")},
                {"account_code": credit_acct, "debit": Decimal("0.00"), "credit": refund.amount},
            ],
        )

        refund.journal_id = entry.id
        refund.status = "PAID"
        refund.approved_by = self.actor.id
        refund.approved_at = utcnow()
        refund.processed_at = utcnow()
        refund.processed_by = self.actor.id
        refund.approval_notes = notes
        self.db.flush()
        self.event("billing.refund_approved", refund)
        return refund

    def get_or_create_resident_fund_account(self, client_id: UUID, admission_id: Optional[UUID] = None) -> ResidentFundAccount:
        account = self.db.query(ResidentFundAccount).filter(
            ResidentFundAccount.facility_id == self.facility_id,
            ResidentFundAccount.client_id == client_id,
        ).first()
        if not account:
            ref_code = generate_reference_code(self.db, self.facility_id, "RESIDENT_FUND")
            account = ResidentFundAccount(
                facility_id=self.facility_id,
                client_id=client_id,
                admission_id=admission_id,
                reference_code=ref_code,
                current_balance=Decimal("0.00"),
                is_active=True,
            )
            self.db.add(account)
            self.db.flush()
        return account

    def deposit_resident_funds(self, account_id: UUID, data: ResidentFundDepositIn) -> ResidentFundTransaction:
        account = self.db.get(ResidentFundAccount, account_id)
        if not account or account.facility_id != self.facility_id:
            raise HTTPException(404, "Resident fund account not found")

        new_balance = account.current_balance + data.amount
        account.current_balance = new_balance

        debit_acct = PAYMENT_ACCOUNT_BY_METHOD.get(data.payment_method.upper(), "1000")
        ledger = FinanceLedgerService(self.db, self.request, self.actor)
        entry = ledger.post_journal(
            entry_date=utcnow().date(),
            reference=f"RFA-DEP-{account.reference_code}",
            description=f"Resident pocket money deposit for {account.reference_code}: {data.description}",
            source_module="RESIDENT_FUNDS",
            source_id=str(account.id),
            posting_type="DEPOSIT",
            lines=[
                {"account_code": debit_acct, "debit": data.amount, "credit": Decimal("0.00")},
                {"account_code": "2200", "debit": Decimal("0.00"), "credit": data.amount},
            ],
        )

        txn = ResidentFundTransaction(
            account_id=account.id,
            transaction_type="DEPOSIT",
            amount=data.amount,
            running_balance=new_balance,
            description=data.description,
            receipt_reference=data.receipt_reference,
            payment_method=data.payment_method,
            authorized_by_id=self.actor.id,
            journal_id=entry.id,
        )
        self.db.add(txn)
        self.db.flush()
        self.event("resident_funds.deposited", txn)
        return txn

    def withdraw_resident_funds(self, account_id: UUID, data: ResidentFundWithdrawIn) -> ResidentFundTransaction:
        account = self.db.get(ResidentFundAccount, account_id)
        if not account or account.facility_id != self.facility_id:
            raise HTTPException(404, "Resident fund account not found")

        if account.current_balance < data.amount:
            raise HTTPException(400, f"Insufficient funds: available KES {account.current_balance}, requested KES {data.amount}")

        new_balance = account.current_balance - data.amount
        account.current_balance = new_balance

        ledger = FinanceLedgerService(self.db, self.request, self.actor)
        entry = ledger.post_journal(
            entry_date=utcnow().date(),
            reference=f"RFA-WTH-{account.reference_code}",
            description=f"Resident pocket money {data.transaction_type.lower()} for {account.reference_code}: {data.description}",
            source_module="RESIDENT_FUNDS",
            source_id=str(account.id),
            posting_type="WITHDRAWAL",
            lines=[
                {"account_code": "2200", "debit": data.amount, "credit": Decimal("0.00")},
                {"account_code": "1000", "debit": Decimal("0.00"), "credit": data.amount},
            ],
        )

        txn = ResidentFundTransaction(
            account_id=account.id,
            transaction_type=data.transaction_type,
            amount=data.amount,
            running_balance=new_balance,
            description=data.description,
            payment_method="CASH",
            authorized_by_id=self.actor.id,
            journal_id=entry.id,
        )
        self.db.add(txn)
        self.db.flush()
        self.event("resident_funds.withdrawn", txn)
        return txn

    # =========================================================================
    # Phase 26.6 - Sprint E: Discharge Financial Clearance & Statements
    # =========================================================================

    def review_discharge_clearance(self, admission_id: UUID, data: DischargeClearanceReviewIn) -> DischargeFinancialClearance:
        admission = self.db.get(Admission, admission_id)
        if not admission or admission.facility_id != self.facility_id:
            raise HTTPException(404, "Admission not found")

        summary = self.get_client_financial_account(admission.client_id, admission.id)

        clearance = self.db.query(DischargeFinancialClearance).filter(
            DischargeFinancialClearance.admission_id == admission_id
        ).first()

        ref_code = clearance.reference_code if clearance else generate_reference_code(self.db, self.facility_id, "DISCHARGE_CLEARANCE")

        if not clearance:
            clearance = DischargeFinancialClearance(
                facility_id=self.facility_id,
                client_id=admission.client_id,
                admission_id=admission_id,
                reference_code=ref_code,
            )
            self.db.add(clearance)

        clearance.total_charges = summary.total_charges
        clearance.total_payments = summary.total_payments
        clearance.total_credits = summary.total_credits
        clearance.total_refunds = summary.total_refunds
        clearance.total_writeoffs = summary.total_writeoffs
        clearance.outstanding_balance = summary.outstanding_balance

        if summary.outstanding_balance > Decimal("0.00"):
            if not data.payment_plan_id and not data.is_authorized_exception:
                raise HTTPException(400, "Outstanding balance exists: Requires an active payment plan or authorized supervisory exception.")
            clearance.status = "PAYMENT_PLAN" if data.payment_plan_id else "AUTHORIZED_EXCEPTION"
            clearance.has_payment_plan = bool(data.payment_plan_id)
            clearance.payment_plan_id = data.payment_plan_id
            clearance.is_authorized_exception = data.is_authorized_exception
            clearance.exception_reason = data.exception_reason
            clearance.collection_owner = data.collection_owner
        elif summary.outstanding_balance == Decimal("0.00") and summary.credit_balance == Decimal("0.00"):
            clearance.status = "CLEARED"
        elif summary.credit_balance > Decimal("0.00"):
            clearance.status = "REFUND_DUE"

        clearance.reviewed_by_id = self.actor.id
        clearance.notes = data.notes
        self.db.flush()
        self.event("billing.discharge_clearance_reviewed", clearance)
        return clearance

    def approve_discharge_clearance(self, clearance_id: UUID, notes: str = "") -> DischargeFinancialClearance:
        clearance = self.db.get(DischargeFinancialClearance, clearance_id)
        if not clearance or clearance.facility_id != self.facility_id:
            raise HTTPException(404, "Discharge clearance record not found")
        if clearance.reviewed_by_id == self.actor.id:
            raise HTTPException(403, "Segregation of duties violation: Reviewer cannot approve their own discharge clearance.")

        if clearance.is_authorized_exception:
            clearance.exception_approved_by_id = self.actor.id
        clearance.approved_by_id = self.actor.id
        clearance.clearance_date = utcnow()
        if notes:
            clearance.notes = f"{clearance.notes} | Approval: {notes}".strip(" |")
        self.db.flush()
        self.event("billing.discharge_clearance_approved", clearance)
        return clearance

    def get_client_financial_account(self, client_id: UUID, admission_id: Optional[UUID] = None) -> ClientFinancialAccountSummary:
        client = self.db.get(Client, client_id)
        if not client or client.facility_id != self.facility_id:
            raise HTTPException(404, "Client not found")

        admission = self.db.get(Admission, admission_id) if admission_id else (
            self.db.query(Admission).filter(
                Admission.client_id == client_id,
                Admission.facility_id == self.facility_id,
            ).order_by(Admission.admission_date.desc()).first()
        )

        inv_query = self.db.query(func.sum(Invoice.total_amount)).filter(
            Invoice.client_id == client_id,
            Invoice.facility_id == self.facility_id,
            Invoice.status != "CANCELLED",
        )
        if admission:
            inv_query = inv_query.filter(Invoice.admission_id == admission.id)
        raw_charges = inv_query.scalar()
        total_charges = money(raw_charges) if raw_charges is not None else Decimal("0.00")

        alloc_query = self.db.query(func.sum(PaymentAllocation.amount)).join(Invoice).filter(
            Invoice.client_id == client_id,
            Invoice.facility_id == self.facility_id,
        )
        if admission:
            alloc_query = alloc_query.filter(Invoice.admission_id == admission.id)
        raw_allocs = alloc_query.scalar()
        total_payments = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")

        cn_query = self.db.query(func.sum(CreditNote.amount)).join(Invoice).filter(
            Invoice.client_id == client_id,
            Invoice.facility_id == self.facility_id,
            CreditNote.status.in_(["POSTED", "APPROVED"]),
        )
        if admission:
            cn_query = cn_query.filter(Invoice.admission_id == admission.id)
        raw_cns = cn_query.scalar()
        total_credits = money(raw_cns) if raw_cns is not None else Decimal("0.00")

        wo_query = self.db.query(func.sum(WriteOff.amount)).join(Invoice).filter(
            Invoice.client_id == client_id,
            Invoice.facility_id == self.facility_id,
            WriteOff.status.in_(["POSTED", "APPROVED"]),
        )
        if admission:
            wo_query = wo_query.filter(Invoice.admission_id == admission.id)
        raw_wos = wo_query.scalar()
        total_writeoffs = money(raw_wos) if raw_wos is not None else Decimal("0.00")

        ref_query = self.db.query(func.sum(Refund.amount)).filter(
            Refund.client_id == client_id,
            Refund.facility_id == self.facility_id,
            Refund.status.in_(["PAID", "APPROVED", "COMPLETED"]),
        )
        raw_refs = ref_query.scalar()
        total_refunds = money(raw_refs) if raw_refs is not None else Decimal("0.00")

        net_diff = total_charges - total_credits - total_payments + total_refunds - total_writeoffs
        outstanding_balance = max(Decimal("0.00"), net_diff)
        credit_balance = max(Decimal("0.00"), -net_diff)

        today = date.today()
        overdue_query = self.db.query(Invoice).filter(
            Invoice.client_id == client_id,
            Invoice.facility_id == self.facility_id,
            Invoice.due_date < today,
            Invoice.status.in_(["ISSUED", "PARTIAL"]),
        )
        if admission:
            overdue_query = overdue_query.filter(Invoice.admission_id == admission.id)
        overdue_invoices = overdue_query.all()
        overdue_amount = sum((self.get_invoice_balance(inv.id) for inv in overdue_invoices), Decimal("0.00"))

        plan = self.db.query(PaymentPlan).filter(
            PaymentPlan.client_id == client_id,
            PaymentPlan.status.in_(["ACTIVE", "ON_TRACK", "OVERDUE"]),
        ).order_by(PaymentPlan.created_at.desc()).first()

        clearance = self.db.query(DischargeFinancialClearance).filter(
            DischargeFinancialClearance.admission_id == admission.id
        ).first() if admission else None

        return ClientFinancialAccountSummary(
            client_id=client.id,
            client_name=f"{client.first_name} {client.surname}",
            client_reference=client.client_number,
            admission_id=admission.id if admission else None,
            admission_number=admission.admission_number if admission else None,
            programme=admission.programme if admission else None,
            total_charges=total_charges,
            total_credits=total_credits,
            total_payments=total_payments,
            total_refunds=total_refunds,
            total_writeoffs=total_writeoffs,
            outstanding_balance=outstanding_balance,
            credit_balance=credit_balance,
            overdue_amount=overdue_amount,
            active_payment_plan_id=plan.id if plan else None,
            active_payment_plan_status=plan.status if plan else None,
            financial_clearance_status=clearance.status if clearance else "NOT_REVIEWED",
        )

    get_client_financial_summary = get_client_financial_account

    def get_client_statement(self, client_id: UUID, admission_id: Optional[UUID] = None) -> dict:
        summary = self.get_client_financial_account(client_id, admission_id)
        
        # Build chronological transactions list
        txns = []
        # Invoices
        inv_q = self.db.query(Invoice).filter(
            Invoice.client_id == client_id,
            Invoice.facility_id == self.facility_id,
            Invoice.status != "CANCELLED",
        )
        if admission_id:
            inv_q = inv_q.filter(Invoice.admission_id == admission_id)
        for inv in inv_q.all():
            txns.append({
                "date": inv.issue_date.isoformat(),
                "reference": inv.invoice_number,
                "type": "INVOICE",
                "description": f"Invoice: {inv.notes or 'Charges'}",
                "debit": float(inv.total_amount),
                "credit": 0.0,
            })

        # Allocations
        alloc_q = self.db.query(PaymentAllocation, Payment).join(Payment, PaymentAllocation.payment_id == Payment.id).join(Invoice, PaymentAllocation.invoice_id == Invoice.id).filter(
            Invoice.client_id == client_id,
            Invoice.facility_id == self.facility_id,
        )
        if admission_id:
            alloc_q = alloc_q.filter(Invoice.admission_id == admission_id)
        for alloc, pay in alloc_q.all():
            txns.append({
                "date": pay.payment_date.date().isoformat() if hasattr(pay.payment_date, "date") else str(pay.payment_date)[:10],
                "reference": pay.transaction_reference,
                "type": "PAYMENT",
                "description": f"Payment via {pay.payment_method}",
                "debit": 0.0,
                "credit": float(alloc.amount),
            })

        # Credit Notes
        cn_q = self.db.query(CreditNote).join(Invoice).filter(
            Invoice.client_id == client_id,
            Invoice.facility_id == self.facility_id,
            CreditNote.status.in_(["POSTED", "APPROVED"]),
        )
        if admission_id:
            cn_q = cn_q.filter(Invoice.admission_id == admission_id)
        for cn in cn_q.all():
            txns.append({
                "date": cn.issued_at.date().isoformat() if hasattr(cn.issued_at, "date") else str(cn.issued_at)[:10],
                "reference": cn.credit_number,
                "type": "CREDIT_NOTE",
                "description": f"Credit Note: {cn.reason}",
                "debit": 0.0,
                "credit": float(cn.amount),
            })

        # Sort chronologically
        txns.sort(key=lambda x: x["date"])

        # Calculate running balance
        running = Decimal("0.00")
        for t in txns:
            running += Decimal(str(t["debit"])) - Decimal(str(t["credit"]))
            t["running_balance"] = float(running)

        return {
            "summary": summary.model_dump(),
            "transactions": txns,
        }

    def get_sponsor_statement(self, sponsor_id: UUID) -> SponsorStatementSummary:
        sponsor = self.db.get(Sponsor, sponsor_id)
        if not sponsor or sponsor.facility_id != self.facility_id:
            raise HTTPException(404, "Sponsor not found")

        # Find all client allocations linked to this sponsor
        allocations = self.db.query(InvoicePayerAllocation, Invoice).join(Invoice).filter(
            InvoicePayerAllocation.sponsor_id == sponsor_id,
            Invoice.facility_id == self.facility_id,
        ).all()

        client_rows = {}
        total_charges = Decimal("0.00")
        total_paid = Decimal("0.00")

        for alloc, inv in allocations:
            total_charges += alloc.allocated_amount
            total_paid += alloc.paid_amount

            client = self.db.get(Client, inv.client_id)
            adm = self.db.get(Admission, inv.admission_id) if inv.admission_id else None

            c_id = str(inv.client_id)
            if c_id not in client_rows:
                client_rows[c_id] = SponsorStatementClientRow(
                    client_id=c_id,
                    client_name=f"{client.first_name} {client.surname}" if client else "Unknown",
                    client_reference=client.client_number if client else "",
                    admission_number=adm.admission_number if adm else "N/A",
                    total_charges=Decimal("0.00"),
                    total_paid=Decimal("0.00"),
                    balance=Decimal("0.00"),
                )

            client_rows[c_id].total_charges += alloc.allocated_amount
            client_rows[c_id].total_paid += alloc.paid_amount
            client_rows[c_id].balance = max(Decimal("0.00"), client_rows[c_id].total_charges - client_rows[c_id].total_paid)

        return SponsorStatementSummary(
            sponsor_id=sponsor.id,
            sponsor_name=sponsor.name,
            sponsor_reference=sponsor.reference_code,
            sponsor_type=sponsor.sponsor_type,
            credit_limit=sponsor.credit_limit,
            total_charges=total_charges,
            total_paid=total_paid,
            outstanding_balance=max(Decimal("0.00"), total_charges - total_paid),
            clients=list(client_rows.values()),
        )

    def log_export_audit(
        self,
        export_format: str,
        report_type: str,
        reference_code: str = "",
        filter_parameters: str = "",
        reason: str = "",
    ) -> BillingExportAudit:
        row = BillingExportAudit(
            facility_id=self.facility_id,
            user_id=self.actor.id,
            export_format=export_format,
            report_type=report_type,
            reference_code=reference_code,
            filter_parameters=filter_parameters,
            reason=reason,
        )
        self.db.add(row)
        self.db.flush()
        return row

    # Alias for export audit
    record_export_audit = log_export_audit

