"""Billing and financial API routes."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import math
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission, require_any_permission
from app.core.money import money
from app.models.identity import User
from app.models.billing import (
    Invoice, InvoiceItem, Payment, Payer, BillingService, MpesaTransaction,
    CreditNote, Refund, WriteOff, Adjustment, PaymentAllocation,
    Sponsor, FinancialAssessment, FinancialQuotation, FinancialQuotationItem, FinancialAgreement,
    PackageServiceInclusion, PackageConsumption, RecurringBillingSchedule,
    InvoicePayerAllocation, PaymentPlan, ResidentFundAccount,
    DischargeFinancialClearance, BillingExportAudit
)
from app.models.clients import Client, Admission
from app.schemas.billing import (
    InvoiceIn, InvoiceOut, PaymentIn, PaymentOut, 
    PayerIn, PayerOut, BillingServiceIn, BillingServiceOut,
    StkPushIn, ManualAllocationIn, MpesaTransactionOut,
    CreditNoteIn, CreditNoteOut, CreditNoteApproveIn,
    WriteOffIn, WriteOffOut, WriteOffApproveIn,
    SponsorIn, SponsorOut,
    FinancialAssessmentIn, FinancialAssessmentOut,
    FinancialQuotationIn, FinancialQuotationOut,
    FinancialAgreementIn, FinancialAgreementOut, FinancialAgreementReviseIn, FinancialAgreementApproveIn,
    PackageServiceInclusionIn, PackageServiceInclusionOut,
    RecurringBillingScheduleIn, RecurringBillingScheduleOut,
    InvoicePayerAllocationIn, InvoicePayerAllocationOut,
    PaymentPlanIn, PaymentPlanOut,
    RefundRequestIn, RefundApproveIn, RefundOut,
    ResidentFundAccountOut, ResidentFundDepositIn, ResidentFundWithdrawIn, ResidentFundTransactionOut,
    DischargeClearanceReviewIn, DischargeClearanceApproveIn, DischargeFinancialClearanceOut,
    ClientFinancialAccountSummary, SponsorStatementSummary, BillingExportRequestIn
)
from app.services.billing import FinanceService
from app.services.mpesa import MpesaService
from app.services.document_engine import FinancialDocumentPdfBuilder, FinancialSpreadsheetExporter


router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)


@router.get("/invoices")
def get_invoices(
    request: Request,
    page: int = 1,
    client_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    query = db.query(Invoice).filter(Invoice.facility_id == actor.facility_id)
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if status:
        query = query.filter(Invoice.status == status)
    
    total = query.count()
    limit = 20
    items = query.order_by(Invoice.issue_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "client_id": str(i.client_id),
                "invoice_number": i.invoice_number,
                "status": i.status,
                "subtotal": str(i.subtotal),
                "discount_amount": str(i.discount_amount),
                "tax_amount": str(i.tax_amount),
                "total_amount": str(i.total_amount),
                "issue_date": i.issue_date.isoformat() if i.issue_date else None,
                "due_date": i.due_date.isoformat() if i.due_date else None
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }


@router.post("/invoices", response_model=InvoiceOut)
def create_invoice(
    request: Request,
    invoice: InvoiceIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    service = FinanceService(db, request, actor)
    created = service.create_invoice(invoice)
    db.commit()
    db.refresh(created)
    return created


@router.post("/payments", response_model=PaymentOut)
def record_payment(
    request: Request,
    payment: PaymentIn,
    invoice_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    service = FinanceService(db, request, actor)
    
    allocations = {}
    if invoice_id:
        allocations[invoice_id] = payment.amount
        
    p = service.record_payment(payment, allocations)
    db.commit()
    db.refresh(p)
    return p


@router.get("/payments")
def get_payments(
    request: Request,
    page: int = 1,
    client_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    query = db.query(Payment).filter(Payment.facility_id == actor.facility_id)
    if client_id:
        query = query.filter(Payment.client_id == client_id)
        
    total = query.count()
    limit = 20
    items = query.order_by(Payment.payment_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "client_id": str(i.client_id) if i.client_id else None,
                "payer_id": str(i.payer_id) if i.payer_id else None,
                "amount": str(i.amount),
                "payment_method": i.payment_method,
                "transaction_reference": i.transaction_reference,
                "status": i.status,
                "payment_date": i.payment_date.isoformat() if i.payment_date else None
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }


@router.get("/payers")
def get_payers(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    query = db.query(Payer).filter(Payer.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(Payer.name.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "name": i.name,
                "payer_type": i.payer_type,
                "contact_person": i.contact_person,
                "contact_phone": i.contact_phone,
                "contact_email": i.contact_email,
                "billing_address": i.billing_address,
                "is_active": i.is_active
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }


@router.post("/payers", response_model=PayerOut)
def create_payer(
    request: Request,
    payer: PayerIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    p = Payer(
        facility_id=actor.facility_id,
        name=payer.name,
        payer_type=payer.payer_type,
        contact_person=payer.contact_person,
        contact_email=payer.contact_email,
        contact_phone=payer.contact_phone,
        billing_address=payer.billing_address,
        is_active=payer.is_active,
        created_by=actor.id,
        updated_by=actor.id
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/services")
def get_services(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    query = db.query(BillingService).filter(BillingService.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(BillingService.name.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "code": i.code,
                "name": i.name,
                "category": i.category,
                "description": i.description,
                "is_active": i.is_active
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }


@router.post("/services", response_model=BillingServiceOut)
def create_service(
    request: Request,
    service_in: BillingServiceIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    s = BillingService(
        facility_id=actor.facility_id,
        code=service_in.code,
        name=service_in.name,
        category=service_in.category,
        description=service_in.description,
        is_active=service_in.is_active,
        created_by=actor.id,
        updated_by=actor.id
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# --- M-Pesa Routes ---

@router.post("/mpesa/stk-push")
def initiate_mpesa_stk_push(
    request: Request,
    payload: StkPushIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.collect_payment"))
):
    mpesa_service = MpesaService(db=db, actor=actor, request=request, facility_id=actor.facility_id)
    try:
        response = mpesa_service.initiate_stk_push(
            facility_id=actor.facility_id,
            client_id=payload.client_id,
            invoice_id=payload.invoice_id,
            phone_number=payload.phone_number,
            amount=payload.amount,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mpesa/callback")
def handle_mpesa_callback(
    request: Request,
    payload: dict[str, Any],
    db: Session = Depends(get_db)
):
    mpesa_service = MpesaService(db=db, request=request)
    result = mpesa_service.process_callback(payload)
    return result


@router.get("/mpesa/reconciliation")
def get_mpesa_reconciliation_list(
    request: Request,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    reconciliation_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.reconcile"))
):
    query = db.query(MpesaTransaction).filter(MpesaTransaction.facility_id == actor.facility_id)
    
    if status:
        query = query.filter(MpesaTransaction.status == status)
    if reconciliation_status:
        query = query.filter(MpesaTransaction.reconciliation_status == reconciliation_status)
    if search:
        search_filter = or_(
            MpesaTransaction.transaction_reference.ilike(f"%{search}%"),
            MpesaTransaction.phone_number.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    total = query.count()
    items = query.order_by(MpesaTransaction.timestamp.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(tx.id),
                "facility_id": str(tx.facility_id),
                "transaction_reference": tx.transaction_reference,
                "phone_number": tx.phone_number,
                "amount": str(tx.amount),
                "timestamp": tx.timestamp.isoformat() if tx.timestamp else None,
                "client_id": str(tx.client_id) if tx.client_id else None,
                "invoice_id": str(tx.invoice_id) if tx.invoice_id else None,
                "payer_id": str(tx.payer_id) if tx.payer_id else None,
                "merchant_request_id": tx.merchant_request_id,
                "checkout_request_id": tx.checkout_request_id,
                "response_code": tx.response_code,
                "customer_message": tx.customer_message,
                "status": tx.status,
                "reconciliation_status": tx.reconciliation_status,
                "reconciled_payment_id": str(tx.reconciled_payment_id) if tx.reconciled_payment_id else None,
                "reconciled_by_id": str(tx.reconciled_by_id) if tx.reconciled_by_id else None,
                "reconciled_at": tx.reconciled_at.isoformat() if tx.reconciled_at else None,
                "reconciliation_notes": tx.reconciliation_notes,
            }
            for tx in items
        ],
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if limit else 1
        }
    }


@router.post("/mpesa/reconciliation/{transaction_id}/allocate")
@router.post("/mpesa/transactions/{transaction_id}/allocate")
def manually_allocate_mpesa(
    transaction_id: UUID,
    payload: ManualAllocationIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.reconcile"))
):
    mpesa_service = MpesaService(db=db, actor=actor, request=request, facility_id=actor.facility_id)
    return mpesa_service.allocate_unmatched_transaction(
        transaction_id=transaction_id,
        invoice_id=payload.invoice_id,
        notes=payload.notes or "",
    )


# --- Client Statement ---

@router.get("/statements/{client_id}")
def get_client_statement(
    client_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    invoices = db.query(Invoice).filter(Invoice.client_id == client_id, Invoice.facility_id == actor.facility_id).all()
    payments = db.query(Payment).filter(Payment.client_id == client_id, Payment.facility_id == actor.facility_id).all()
    
    total_invoiced = sum((i.total_amount for i in invoices if i.status != "CANCELLED"), Decimal("0.00"))
    total_paid = sum((p.amount for p in payments if p.status == "COMPLETED"), Decimal("0.00"))
    
    now = datetime.now(timezone.utc).date()
    ageing = {
        "0-30": Decimal("0.00"),
        "31-60": Decimal("0.00"),
        "61-90": Decimal("0.00"),
        "90+": Decimal("0.00")
    }
    
    for inv in invoices:
        if inv.status in ("PAID", "CANCELLED", "WRITTEN_OFF"):
            continue
            
        raw_allocs = db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == inv.id).scalar()
        allocs = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")
        balance = max(Decimal("0.00"), inv.total_amount - allocs)
        
        if balance > Decimal("0.00") and inv.due_date:
            days_overdue = (now - inv.due_date).days
            if days_overdue <= 30:
                ageing["0-30"] += balance
            elif days_overdue <= 60:
                ageing["31-60"] += balance
            elif days_overdue <= 90:
                ageing["61-90"] += balance
            else:
                ageing["90+"] += balance

    return {
        "client_id": str(client_id),
        "total_invoiced": str(total_invoiced),
        "total_paid": str(total_paid),
        "outstanding_balance": str(max(Decimal("0.00"), total_invoiced - total_paid)),
        "ageing": {k: str(v) for k, v in ageing.items()},
        "invoices": [{"id": str(i.id), "number": i.invoice_number, "date": i.issue_date.isoformat(), "amount": str(i.total_amount), "status": i.status} for i in invoices],
        "payments": [{"id": str(p.id), "date": p.payment_date.isoformat(), "amount": str(p.amount), "method": p.payment_method} for p in payments]
    }


# --- Phase 26.5: Credit Notes Workflow ---

@router.post("/credit-notes", response_model=CreditNoteOut)
def request_credit_note(
    request: Request,
    payload: CreditNoteIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.credit_note.create"))
):
    service = FinanceService(db, request, actor)
    cn = service.create_credit_note(payload)
    db.commit()
    db.refresh(cn)
    return cn


@router.get("/credit-notes")
def get_credit_notes(
    request: Request,
    page: int = 1,
    invoice_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    query = db.query(CreditNote).filter(CreditNote.facility_id == actor.facility_id)
    if invoice_id:
        query = query.filter(CreditNote.invoice_id == invoice_id)
    if status:
        query = query.filter(CreditNote.status == status)

    total = query.count()
    limit = 20
    items = query.order_by(CreditNote.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [
            {
                "id": str(cn.id),
                "credit_number": cn.credit_number,
                "invoice_id": str(cn.invoice_id),
                "amount": str(cn.amount),
                "reason_code": cn.reason_code,
                "reason": cn.reason,
                "status": cn.status,
                "requested_by": str(cn.requested_by) if cn.requested_by else None,
                "requested_at": cn.requested_at.isoformat() if cn.requested_at else None,
                "approved_by": str(cn.approved_by) if cn.approved_by else None,
                "approved_at": cn.approved_at.isoformat() if cn.approved_at else None,
                "approval_notes": cn.approval_notes,
                "created_at": cn.created_at.isoformat() if cn.created_at else None,
            }
            for cn in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }


@router.get("/credit-notes/{id}", response_model=CreditNoteOut)
def get_credit_note_detail(
    id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    cn = db.get(CreditNote, id)
    if not cn or cn.facility_id != actor.facility_id:
        raise HTTPException(404, "Credit note not found")
    return cn


@router.post("/credit-notes/{id}/approve", response_model=CreditNoteOut)
def approve_credit_note(
    id: UUID,
    request: Request,
    payload: CreditNoteApproveIn = CreditNoteApproveIn(),
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.credit_note.approve"))
):
    service = FinanceService(db, request, actor)
    cn = service.approve_credit_note(id, payload.approval_notes)
    db.commit()
    db.refresh(cn)
    return cn


@router.post("/credit-notes/{id}/reject", response_model=CreditNoteOut)
def reject_credit_note(
    id: UUID,
    request: Request,
    payload: CreditNoteApproveIn = CreditNoteApproveIn(),
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.credit_note.approve"))
):
    service = FinanceService(db, request, actor)
    cn = service.reject_credit_note(id, payload.approval_notes)
    db.commit()
    db.refresh(cn)
    return cn


# --- Phase 26.5: Write-Offs Workflow ---

@router.post("/write-offs", response_model=WriteOffOut)
def request_writeoff(
    request: Request,
    payload: WriteOffIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.writeoff.request"))
):
    service = FinanceService(db, request, actor)
    wo = service.create_writeoff(payload)
    db.commit()
    db.refresh(wo)
    return wo


@router.get("/write-offs")
def get_writeoffs(
    request: Request,
    page: int = 1,
    invoice_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    query = db.query(WriteOff).filter(WriteOff.facility_id == actor.facility_id)
    if invoice_id:
        query = query.filter(WriteOff.invoice_id == invoice_id)
    if status:
        query = query.filter(WriteOff.status == status)

    total = query.count()
    limit = 20
    items = query.order_by(WriteOff.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [
            {
                "id": str(wo.id),
                "reference_code": wo.reference_code,
                "invoice_id": str(wo.invoice_id),
                "amount": str(wo.amount),
                "reason": wo.reason,
                "status": wo.status,
                "requested_by": str(wo.requested_by) if wo.requested_by else None,
                "requested_at": wo.requested_at.isoformat() if wo.requested_at else None,
                "approved_by": str(wo.approved_by) if wo.approved_by else None,
                "approved_at": wo.approved_at.isoformat() if wo.approved_at else None,
                "written_off_at": wo.written_off_at.isoformat() if wo.written_off_at else None,
                "approval_notes": wo.approval_notes,
                "created_at": wo.created_at.isoformat() if wo.created_at else None,
            }
            for wo in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }


@router.get("/write-offs/{id}", response_model=WriteOffOut)
def get_writeoff_detail(
    id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    wo = db.get(WriteOff, id)
    if not wo or wo.facility_id != actor.facility_id:
        raise HTTPException(404, "Write-off record not found")
    return wo


@router.post("/write-offs/{id}/approve", response_model=WriteOffOut)
def approve_writeoff(
    id: UUID,
    request: Request,
    payload: WriteOffApproveIn = WriteOffApproveIn(),
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.writeoff.approve"))
):
    service = FinanceService(db, request, actor)
    wo = service.approve_writeoff(id, payload.approval_notes)
    db.commit()
    db.refresh(wo)
    return wo


@router.post("/write-offs/{id}/reject", response_model=WriteOffOut)
def reject_writeoff(
    id: UUID,
    request: Request,
    payload: WriteOffApproveIn = WriteOffApproveIn(),
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.writeoff.approve"))
):
    service = FinanceService(db, request, actor)
    wo = service.reject_writeoff(id, payload.approval_notes)
    db.commit()
    db.refresh(wo)
    return wo


# --- Remediated Legacy Routes ---

@router.post("/adjustments")
def create_adjustment(
    invoice_id: UUID,
    amount: Decimal,
    reason: str,
    adjustment_type: str,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    """Legacy adjustment route: Enforces invoice immutability.
    
    If invoice is finalized (ISSUED, PARTIAL, PAID, OVERDUE), direct mutation is rejected,
    requiring the creation of a formal Credit Note.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
        
    if invoice.status in ("ISSUED", "PARTIAL", "PAID", "OVERDUE"):
        raise HTTPException(
            400,
            "Issued invoices are financially immutable. Direct mutation is prohibited. Please submit a Credit Note request via POST /billing/credit-notes.",
        )

    # For draft invoices, adjust line or total safely
    adj_amount = money(amount)
    adj = Adjustment(
        facility_id=actor.facility_id,
        invoice_id=invoice_id,
        amount=adj_amount,
        reason=reason,
        adjustment_type=adjustment_type,
        created_by=actor.id
    )
    db.add(adj)
    invoice.total_amount = max(Decimal("0.00"), invoice.total_amount + adj_amount)
    db.commit()
    service = FinanceService(db, request, actor)
    service.event("billing.adjustment_created", adj)
    return {"message": "Draft adjustment created", "new_total": str(invoice.total_amount)}


@router.post("/writeoffs")
def create_writeoff_legacy(
    invoice_id: UUID,
    amount: Decimal,
    reason: str,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.writeoff.request"))
):
    """Legacy write-off route: Enforces Maker-Checker.
    
    Routes to write-off request in PENDING_APPROVAL status rather than instant self-approval.
    """
    service = FinanceService(db, request, actor)
    wo = service.create_writeoff(WriteOffIn(invoice_id=invoice_id, amount=amount, reason=reason))
    db.commit()
    return {
        "message": "Write-off requested and awaiting independent financial approval",
        "writeoff_id": str(wo.id),
        "status": wo.status,
    }


# =========================================================================
# Phase 26.6 - Sprint A: Pre-Admission Financial Assessments & Quotations
# =========================================================================

@router.post("/assessments", response_model=FinancialAssessmentOut)
def create_financial_assessment(
    request: Request,
    data: FinancialAssessmentIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.financial_assessment.create"))
):
    service = FinanceService(db, request, actor)
    res = service.create_financial_assessment(data)
    db.commit()
    db.refresh(res)
    return res


@router.get("/assessments")
def list_financial_assessments(
    client_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = FinanceService(db, None, actor)
    items = service.list_financial_assessments(client_id)
    return {
        "items": [
            {
                "id": str(a.id),
                "client_id": str(a.client_id),
                "reference_code": a.reference_code,
                "proposed_programme": a.proposed_programme,
                "expected_duration_days": a.expected_duration_days,
                "primary_payer_type": a.primary_payer_type,
                "primary_payer_name": a.primary_payer_name,
                "estimated_programme_cost": str(a.estimated_programme_cost),
                "deposit_required": str(a.deposit_required),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ]
    }


@router.get("/assessments/{assessment_id}", response_model=FinancialAssessmentOut)
def get_financial_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = FinanceService(db, None, actor)
    return service.get_financial_assessment(assessment_id)


@router.post("/quotations", response_model=FinancialQuotationOut)
def create_quotation(
    request: Request,
    data: FinancialQuotationIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.estimate.create"))
):
    service = FinanceService(db, request, actor)
    res = service.create_quotation(data)
    db.commit()
    db.refresh(res)
    return res


@router.get("/quotations/{quotation_id}", response_model=FinancialQuotationOut)
def get_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = FinanceService(db, None, actor)
    q = service.get_quotation(quotation_id)
    items = db.query(FinancialQuotationItem).filter(FinancialQuotationItem.quotation_id == q.id).all()
    q.items = items
    return q


@router.post("/quotations/{quotation_id}/issue")
def issue_quotation(
    request: Request,
    quotation_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.estimate.issue"))
):
    service = FinanceService(db, request, actor)
    q = service.issue_quotation(quotation_id)
    db.commit()
    return {"message": "Quotation issued successfully", "status": q.status, "reference_code": q.reference_code}


@router.post("/quotations/{quotation_id}/accept")
def accept_quotation(
    request: Request,
    quotation_id: UUID,
    accepted_by: str,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = FinanceService(db, request, actor)
    q = service.accept_quotation(quotation_id, accepted_by)
    db.commit()
    return {"message": "Quotation accepted", "status": q.status, "accepted_by": q.accepted_by}


@router.post("/quotations/{quotation_id}/convert")
def convert_quotation(
    request: Request,
    quotation_id: UUID,
    admission_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.agreement.create"))
):
    service = FinanceService(db, request, actor)
    agreement = service.convert_quotation_to_agreement(quotation_id, admission_id)
    db.commit()
    db.refresh(agreement)
    return {
        "message": "Quotation successfully converted to financial agreement",
        "agreement_id": str(agreement.id),
        "reference_code": agreement.reference_code,
        "status": agreement.status,
    }


@router.get("/quotations/{quotation_id}/pdf")
def get_quotation_pdf(
    quotation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.print"))
):
    service = FinanceService(db, request, actor)
    q = service.get_quotation(quotation_id)
    client = db.get(Client, q.client_id)
    items = db.query(FinancialQuotationItem).filter(FinancialQuotationItem.quotation_id == q.id).all()

    builder = FinancialDocumentPdfBuilder()
    pdf_bytes = builder.generate_quotation_pdf({
        "reference_code": q.reference_code,
        "status": q.status,
        "client_name": f"{client.first_name} {client.surname}" if client else "N/A",
        "client_number": client.client_number if client else "N/A",
        "programme_name": q.programme_name,
        "duration_days": q.duration_days,
        "deposit_required": q.deposit_required,
        "valid_until": q.valid_until,
        "total_amount": q.total_amount,
        "terms_and_conditions": q.terms_and_conditions,
        "items": [
            {
                "category": it.category,
                "description": it.description,
                "quantity": float(it.quantity),
                "unit_price": float(it.unit_price),
                "total_price": float(it.total_price),
            } for it in items
        ]
    })
    service.log_export_audit("PDF", "QUOTATION", q.reference_code, f"quotation_id={q.id}", "Print preview")
    db.commit()
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{q.reference_code}.pdf"'})


# =========================================================================
# Phase 26.6 - Financial Agreements
# =========================================================================

@router.post("/agreements", response_model=FinancialAgreementOut)
def create_financial_agreement(
    request: Request,
    data: FinancialAgreementIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.agreement.create"))
):
    service = FinanceService(db, request, actor)
    res = service.create_financial_agreement(data)
    db.commit()
    db.refresh(res)
    return res


@router.get("/agreements")
def list_financial_agreements(
    client_id: Optional[UUID] = None,
    admission_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    q = db.query(FinancialAgreement).filter(FinancialAgreement.facility_id == actor.facility_id)
    if client_id:
        q = q.filter(FinancialAgreement.client_id == client_id)
    if admission_id:
        q = q.filter(FinancialAgreement.admission_id == admission_id)
    items = q.order_by(FinancialAgreement.created_at.desc()).all()
    return {
        "items": [
            {
                "id": str(a.id),
                "client_id": str(a.client_id),
                "admission_id": str(a.admission_id) if a.admission_id else None,
                "reference_code": a.reference_code,
                "version": a.version,
                "programme_name": a.programme_name,
                "agreed_price": str(a.agreed_price),
                "deposit_amount": str(a.deposit_amount),
                "status": a.status,
                "effective_date": a.effective_date.isoformat(),
            }
            for a in items
        ]
    }


@router.get("/agreements/{agreement_id}", response_model=FinancialAgreementOut)
def get_financial_agreement(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    row = db.get(FinancialAgreement, agreement_id)
    if not row or row.facility_id != actor.facility_id:
        raise HTTPException(404, "Financial agreement not found")
    return row


@router.post("/agreements/{agreement_id}/revise", response_model=FinancialAgreementOut)
def revise_financial_agreement(
    request: Request,
    agreement_id: UUID,
    data: FinancialAgreementReviseIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.agreement.create"))
):
    service = FinanceService(db, request, actor)
    res = service.revise_financial_agreement(agreement_id, data)
    db.commit()
    db.refresh(res)
    return res


@router.post("/agreements/{agreement_id}/approve", response_model=FinancialAgreementOut)
def approve_financial_agreement(
    request: Request,
    agreement_id: UUID,
    data: FinancialAgreementApproveIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.agreement.approve"))
):
    service = FinanceService(db, request, actor)
    res = service.approve_financial_agreement(agreement_id, data.notes)
    db.commit()
    db.refresh(res)
    return res


@router.get("/agreements/{agreement_id}/pdf")
def get_financial_agreement_pdf(
    agreement_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.print"))
):
    service = FinanceService(db, request, actor)
    agreement = db.get(FinancialAgreement, agreement_id)
    if not agreement or agreement.facility_id != actor.facility_id:
        raise HTTPException(404, "Agreement not found")
    client = db.get(Client, agreement.client_id)
    adm = db.get(Admission, agreement.admission_id) if agreement.admission_id else None

    builder = FinancialDocumentPdfBuilder()
    pdf_bytes = builder.generate_statement_pdf({
        "summary": {
            "client_reference": f"{agreement.reference_code} v{agreement.version}",
            "financial_clearance_status": agreement.status,
            "client_name": f"{client.first_name} {client.surname}" if client else "N/A",
            "admission_number": adm.admission_number if adm else "Pre-Admission",
            "total_charges": agreement.agreed_price,
            "total_payments": agreement.deposit_paid,
            "outstanding_balance": agreement.agreed_price - agreement.deposit_paid,
        },
        "transactions": [
            {
                "date": agreement.effective_date.isoformat(),
                "reference": agreement.reference_code,
                "description": f"Agreed Package: {agreement.programme_name} ({agreement.inclusions[:80]})",
                "debit": float(agreement.agreed_price),
                "credit": 0.0,
                "running_balance": float(agreement.agreed_price),
            }
        ]
    })
    service.log_export_audit("PDF", "FINANCIAL_AGREEMENT", agreement.reference_code, f"agreement_id={agreement.id}", "Print preview")
    db.commit()
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{agreement.reference_code}_v{agreement.version}.pdf"'})


# =========================================================================
# Phase 26.6 - Sprint C: Sponsors & Split Payer Allocation
# =========================================================================

@router.post("/sponsors", response_model=SponsorOut)
def create_sponsor(
    request: Request,
    data: SponsorIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    service = FinanceService(db, request, actor)
    sponsor = service.create_sponsor(data)
    db.commit()
    db.refresh(sponsor)
    return sponsor


@router.get("/sponsors", response_model=list[SponsorOut])
def list_sponsors(
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = FinanceService(db, None, actor)
    return service.list_sponsors()


@router.post("/invoices/{invoice_id}/payers", response_model=list[InvoicePayerAllocationOut])
def allocate_invoice_payers(
    request: Request,
    invoice_id: UUID,
    allocations: list[InvoicePayerAllocationIn],
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    service = FinanceService(db, request, actor)
    res = service.allocate_invoice_payers(invoice_id, allocations)
    db.commit()
    return res


@router.get("/sponsors/{sponsor_id}/statement", response_model=SponsorStatementSummary)
def get_sponsor_statement(
    sponsor_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = FinanceService(db, None, actor)
    return service.get_sponsor_statement(sponsor_id)


# =========================================================================
# Phase 26.6 - Client Financial Account & Documents
# =========================================================================

@router.get("/clients/{client_id}/financial-account", response_model=ClientFinancialAccountSummary)
def get_client_financial_account(
    client_id: UUID,
    admission_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = FinanceService(db, None, actor)
    return service.get_client_financial_account(client_id, admission_id)


@router.get("/clients/{client_id}/statement")
def get_client_statement(
    client_id: UUID,
    admission_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    service = FinanceService(db, None, actor)
    return service.get_client_statement(client_id, admission_id)


@router.get("/clients/{client_id}/statement/pdf")
def get_client_statement_pdf(
    client_id: UUID,
    request: Request,
    admission_id: Optional[UUID] = None,
    is_final: bool = False,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.print"))
):
    service = FinanceService(db, request, actor)
    statement_data = service.get_client_statement(client_id, admission_id)
    builder = FinancialDocumentPdfBuilder()
    pdf_bytes = builder.generate_statement_pdf(statement_data, is_final=is_final)
    ref = statement_data["summary"].get("client_reference", "STATEMENT")
    service.log_export_audit("PDF", "CLIENT_STATEMENT", ref, f"client_id={client_id}", "Print statement")
    db.commit()
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{ref}_statement.pdf"'})


@router.get("/invoices/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.print"))
):
    service = FinanceService(db, request, actor)
    inv = db.get(Invoice, invoice_id)
    if not inv or inv.facility_id != actor.facility_id:
        raise HTTPException(404, "Invoice not found")
    client = db.get(Client, inv.client_id)
    adm = db.get(Admission, inv.admission_id) if inv.admission_id else None
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).all()

    # Balance due calculation
    balance_due = service.get_invoice_balance(inv.id)
    raw_allocs = db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == inv.id).scalar()
    amount_paid = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")

    builder = FinancialDocumentPdfBuilder()
    pdf_bytes = builder.generate_invoice_pdf({
        "invoice_number": inv.invoice_number,
        "status": inv.status,
        "client_name": f"{client.first_name} {client.surname}" if client else "N/A",
        "client_number": client.client_number if client else "N/A",
        "admission_number": adm.admission_number if adm else "N/A",
        "issue_date": inv.issue_date,
        "due_date": inv.due_date,
        "subtotal": inv.subtotal,
        "discount_amount": inv.discount_amount,
        "tax_amount": inv.tax_amount,
        "total_amount": inv.total_amount,
        "amount_paid": amount_paid,
        "balance_due": balance_due,
        "items": [
            {
                "description": it.description,
                "quantity": float(it.quantity),
                "unit_price": float(it.unit_price),
                "discount": float(it.discount),
                "total_price": float(it.total_price),
            } for it in items
        ]
    })
    service.log_export_audit("PDF", "INVOICE", inv.invoice_number, f"invoice_id={inv.id}", "Print preview")
    db.commit()
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{inv.invoice_number}.pdf"'})


@router.get("/payments/{payment_id}/receipt/pdf")
def get_payment_receipt_pdf(
    payment_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.print"))
):
    service = FinanceService(db, request, actor)
    pay = db.get(Payment, payment_id)
    if not pay or pay.facility_id != actor.facility_id:
        raise HTTPException(404, "Payment not found")
    client = db.get(Client, pay.client_id) if pay.client_id else None

    # Derive receipt reference
    receipt_ref = f"RCT-{pay.transaction_reference[-8:]}" if pay.transaction_reference else f"RCT-{str(pay.id)[:8]}"

    # Invoices settled
    allocs = db.query(PaymentAllocation).filter(PaymentAllocation.payment_id == pay.id).all()
    inv_nums = []
    for a in allocs:
        inv = db.get(Invoice, a.invoice_id)
        if inv:
            inv_nums.append(f"{inv.invoice_number} (KES {a.amount})")
    invoices_settled = ", ".join(inv_nums) if inv_nums else "Direct Payment / Account Deposit"

    summary = service.get_client_financial_account(pay.client_id) if pay.client_id else None
    remaining_balance = summary.outstanding_balance if summary else Decimal("0.00")

    builder = FinancialDocumentPdfBuilder()
    pdf_bytes = builder.generate_receipt_pdf({
        "receipt_number": receipt_ref,
        "received_from": f"{client.first_name} {client.surname}" if client else "Client",
        "client_number": client.client_number if client else "N/A",
        "admission_number": summary.admission_number if summary else "N/A",
        "payment_date": pay.payment_date,
        "payment_method": pay.payment_method,
        "transaction_reference": pay.transaction_reference,
        "amount": pay.amount,
        "invoices_settled": invoices_settled,
        "remaining_balance": remaining_balance,
        "received_by": getattr(actor, "full_name", None) or getattr(actor, "email", "Authorized Cashier"),
    })
    service.log_export_audit("PDF", "RECEIPT", receipt_ref, f"payment_id={pay.id}", "Print receipt")
    db.commit()
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{receipt_ref}.pdf"'})


@router.get("/documents/pdf")
def get_unified_document_pdf(
    document_type: str,
    reference_id: UUID,
    request: Request,
    admission_id: Optional[UUID] = None,
    is_final: bool = False,
    db: Session = Depends(get_db),
    actor=Depends(require_any_permission("finance.print", "billing.view"))
):
    service = FinanceService(db, request, actor)
    builder = FinancialDocumentPdfBuilder()
    doc_type = document_type.upper().strip()

    if doc_type == "INVOICE":
        inv = db.get(Invoice, reference_id)
        if not inv or inv.facility_id != actor.facility_id:
            inv = db.query(Invoice).filter(
                Invoice.client_id == reference_id,
                Invoice.facility_id == actor.facility_id,
            ).order_by(Invoice.issue_date.desc(), Invoice.created_at.desc()).first()

        if inv:
            client = db.get(Client, inv.client_id)
            adm = db.get(Admission, inv.admission_id) if inv.admission_id else None
            items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).all()
            balance_due = service.get_invoice_balance(inv.id)
            raw_allocs = db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == inv.id).scalar()
            amount_paid = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")

            pdf_bytes = builder.generate_invoice_pdf({
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "client_name": f"{client.first_name} {client.surname}" if client else "N/A",
                "client_number": client.client_number if client else "N/A",
                "admission_number": adm.admission_number if adm else "N/A",
                "issue_date": inv.issue_date,
                "due_date": inv.due_date,
                "subtotal": inv.subtotal,
                "discount_amount": inv.discount_amount,
                "tax_amount": inv.tax_amount,
                "total_amount": inv.total_amount,
                "amount_paid": amount_paid,
                "balance_due": balance_due,
                "items": [
                    {
                        "description": it.description,
                        "quantity": float(it.quantity),
                        "unit_price": float(it.unit_price),
                        "discount": float(it.discount),
                        "total_price": float(it.total_price),
                    } for it in items
                ]
            })
            service.log_export_audit("PDF", "INVOICE", inv.invoice_number, f"invoice_id={inv.id}", "Print preview")
            db.commit()
            return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{inv.invoice_number}.pdf"'})
        else:
            client = db.get(Client, reference_id)
            if client and client.facility_id == actor.facility_id:
                adm = db.query(Admission).filter(Admission.client_id == client.id).order_by(Admission.admission_date.desc()).first()
                pro_forma_number = f"PROFORMA-{client.client_number}"
                pdf_bytes = builder.generate_invoice_pdf({
                    "invoice_number": pro_forma_number,
                    "status": "PRO FORMA",
                    "client_name": f"{client.first_name} {client.surname}",
                    "client_number": client.client_number,
                    "admission_number": adm.admission_number if adm else "Pending Admission",
                    "issue_date": date.today(),
                    "due_date": date.today() + timedelta(days=30),
                    "subtotal": Decimal("0.00"),
                    "discount_amount": Decimal("0.00"),
                    "tax_amount": Decimal("0.00"),
                    "total_amount": Decimal("0.00"),
                    "amount_paid": Decimal("0.00"),
                    "balance_due": Decimal("0.00"),
                    "items": [
                        {
                            "description": f"Admission & Rehabilitation Package ({adm.admission_number})" if adm else "Rehabilitation Services - Pending Billing Run",
                            "quantity": 1,
                            "unit_price": 0.0,
                            "discount": 0.0,
                            "total_price": 0.0,
                        }
                    ]
                })
                service.log_export_audit("PDF", "INVOICE", pro_forma_number, f"client_id={client.id}", "Print pro-forma invoice")
                db.commit()
                return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{pro_forma_number}.pdf"'})
            raise HTTPException(404, "Invoice or client not found")

    elif doc_type == "STATEMENT":
        client_id = reference_id
        client = db.get(Client, client_id)
        if not client:
            adm = db.get(Admission, reference_id)
            if adm:
                client_id = adm.client_id
                client = db.get(Client, client_id)
        if not client or client.facility_id != actor.facility_id:
            raise HTTPException(404, "Client statement record not found")
        statement_data = service.get_client_statement(client_id, admission_id)
        pdf_bytes = builder.generate_statement_pdf(statement_data, is_final=is_final)
        ref = statement_data["summary"].get("client_reference", "STATEMENT")
        service.log_export_audit("PDF", "CLIENT_STATEMENT", ref, f"client_id={client_id}", "Print statement")
        db.commit()
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{ref}_statement.pdf"'})

    elif doc_type == "RECEIPT":
        pay = db.get(Payment, reference_id)
        if not pay or pay.facility_id != actor.facility_id:
            pay = db.query(Payment).filter(
                Payment.client_id == reference_id,
                Payment.facility_id == actor.facility_id,
            ).order_by(Payment.payment_date.desc(), Payment.created_at.desc()).first()

        if pay:
            client = db.get(Client, pay.client_id) if pay.client_id else None
            receipt_ref = f"RCT-{pay.transaction_reference[-8:]}" if pay.transaction_reference else f"RCT-{str(pay.id)[:8]}"
            allocs = db.query(PaymentAllocation).filter(PaymentAllocation.payment_id == pay.id).all()
            inv_nums = []
            for a in allocs:
                inv = db.get(Invoice, a.invoice_id)
                if inv:
                    inv_nums.append(f"{inv.invoice_number} (KES {a.amount})")
            invoices_settled = ", ".join(inv_nums) if inv_nums else "Direct Payment / Account Deposit"
            summary = service.get_client_financial_account(pay.client_id) if pay.client_id else None
            remaining_balance = summary.outstanding_balance if summary else Decimal("0.00")

            pdf_bytes = builder.generate_receipt_pdf({
                "receipt_number": receipt_ref,
                "received_from": f"{client.first_name} {client.surname}" if client else "Client",
                "client_number": client.client_number if client else "N/A",
                "admission_number": summary.admission_number if summary else "N/A",
                "payment_date": pay.payment_date,
                "payment_method": pay.payment_method,
                "transaction_reference": pay.transaction_reference,
                "amount": pay.amount,
                "invoices_settled": invoices_settled,
                "remaining_balance": remaining_balance,
                "received_by": getattr(actor, "full_name", None) or getattr(actor, "email", "Authorized Cashier"),
            })
            service.log_export_audit("PDF", "RECEIPT", receipt_ref, f"payment_id={pay.id}", "Print receipt")
            db.commit()
            return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{receipt_ref}.pdf"'})
        else:
            client = db.get(Client, reference_id)
            if client and client.facility_id == actor.facility_id:
                summary = service.get_client_financial_account(client.id)
                provisional_ref = f"RCT-PROV-{client.client_number}"
                pdf_bytes = builder.generate_receipt_pdf({
                    "receipt_number": provisional_ref,
                    "received_from": f"{client.first_name} {client.surname}",
                    "client_number": client.client_number,
                    "admission_number": summary.admission_number if summary else "N/A",
                    "payment_date": date.today(),
                    "payment_method": "NO PAYMENTS RECORDED",
                    "transaction_reference": "N/A",
                    "amount": Decimal("0.00"),
                    "invoices_settled": "No payments recorded to date",
                    "remaining_balance": summary.outstanding_balance if summary else Decimal("0.00"),
                    "received_by": getattr(actor, "full_name", None) or getattr(actor, "email", "Authorized Cashier"),
                })
                service.log_export_audit("PDF", "RECEIPT", provisional_ref, f"client_id={client.id}", "Print provisional receipt")
                db.commit()
                return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{provisional_ref}.pdf"'})
            raise HTTPException(404, "Payment or client not found")

    elif doc_type == "DISCHARGE_CLEARANCE":
        clr = db.get(DischargeFinancialClearance, reference_id)
        if not clr or clr.facility_id != actor.facility_id:
            clr = db.query(DischargeFinancialClearance).filter(
                DischargeFinancialClearance.admission_id == reference_id,
                DischargeFinancialClearance.facility_id == actor.facility_id,
            ).order_by(DischargeFinancialClearance.created_at.desc()).first()
        if not clr:
            clr = db.query(DischargeFinancialClearance).join(
                Admission, DischargeFinancialClearance.admission_id == Admission.id
            ).filter(
                Admission.client_id == reference_id,
                DischargeFinancialClearance.facility_id == actor.facility_id,
            ).order_by(DischargeFinancialClearance.created_at.desc()).first()

        if clr:
            adm = db.get(Admission, clr.admission_id)
            client = db.get(Client, adm.client_id) if adm else None
            approver = db.get(User, clr.approved_by_id) if clr.approved_by_id else None
            pdf_bytes = builder.generate_discharge_clearance_pdf({
                "reference_code": clr.reference_code,
                "status": clr.status,
                "client_name": f"{client.first_name} {client.surname}" if client else "N/A",
                "client_code": client.client_number if client else "N/A",
                "admission_code": adm.admission_number if adm else "N/A",
                "clearance_date": clr.approved_at or clr.created_at,
                "approved_by": (getattr(approver, "full_name", None) or getattr(approver, "email", None)) if approver else "Finance Authority",
                "total_charges": clr.total_charges,
                "total_payments": clr.total_payments,
                "total_credits": clr.total_credits,
                "total_writeoffs": clr.total_writeoffs,
                "outstanding_balance": clr.outstanding_balance,
                "is_authorized_exception": clr.is_authorized_exception,
                "exception_reason": clr.exception_reason,
            })
            service.log_export_audit("PDF", "DISCHARGE_CLEARANCE", clr.reference_code, f"clearance_id={clr.id}", "Print discharge clearance")
            db.commit()
            return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{clr.reference_code}_clearance.pdf"'})
        else:
            client = db.get(Client, reference_id)
            if client and client.facility_id == actor.facility_id:
                summary = service.get_client_financial_account(client.id)
                adm = db.query(Admission).filter(Admission.client_id == client.id).order_by(Admission.admission_date.desc()).first()
                prov_code = f"PROV-CLR-{client.client_number}"
                pdf_bytes = builder.generate_discharge_clearance_pdf({
                    "reference_code": prov_code,
                    "status": "PRE-DISCHARGE REVIEW",
                    "client_name": f"{client.first_name} {client.surname}",
                    "client_code": client.client_number,
                    "admission_code": adm.admission_number if adm else "N/A",
                    "clearance_date": date.today(),
                    "approved_by": "Pending Final Review",
                    "total_charges": summary.total_charges,
                    "total_payments": summary.total_payments,
                    "total_credits": summary.total_credits,
                    "total_writeoffs": summary.total_writeoffs,
                    "outstanding_balance": summary.outstanding_balance,
                    "is_authorized_exception": False,
                    "exception_reason": "",
                })
                service.log_export_audit("PDF", "DISCHARGE_CLEARANCE", prov_code, f"client_id={client.id}", "Print provisional clearance")
                db.commit()
                return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{prov_code}_clearance.pdf"'})
            raise HTTPException(404, "Discharge clearance record or client not found")

    elif doc_type in ("QUOTATION", "QUOTE"):
        q = db.get(FinancialQuotation, reference_id)
        if not q or q.facility_id != actor.facility_id:
            q = db.query(FinancialQuotation).filter(
                FinancialQuotation.client_id == reference_id,
                FinancialQuotation.facility_id == actor.facility_id,
            ).order_by(FinancialQuotation.created_at.desc()).first()
        if not q:
            raise HTTPException(404, "Quotation not found")
        client = db.get(Client, q.client_id)
        items = db.query(FinancialQuotationItem).filter(FinancialQuotationItem.quotation_id == q.id).all()
        pdf_bytes = builder.generate_quotation_pdf({
            "reference_code": q.reference_code,
            "status": q.status,
            "client_name": f"{client.first_name} {client.surname}" if client else "N/A",
            "client_number": client.client_number if client else "N/A",
            "programme_name": q.programme_name,
            "duration_days": q.duration_days,
            "deposit_required": q.deposit_required,
            "valid_until": q.valid_until,
            "total_amount": q.total_amount,
            "terms_and_conditions": q.terms_and_conditions,
            "items": [
                {
                    "category": it.category,
                    "description": it.description,
                    "quantity": float(it.quantity),
                    "unit_price": float(it.unit_price),
                    "total_price": float(it.total_price),
                } for it in items
            ]
        })
        service.log_export_audit("PDF", "QUOTATION", q.reference_code, f"quotation_id={q.id}", "Print quotation")
        db.commit()
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{q.reference_code}.pdf"'})

    elif doc_type in ("AGREEMENT", "FINANCIAL_AGREEMENT"):
        agreement = db.get(FinancialAgreement, reference_id)
        if not agreement or agreement.facility_id != actor.facility_id:
            agreement = db.query(FinancialAgreement).filter(
                FinancialAgreement.client_id == reference_id,
                FinancialAgreement.facility_id == actor.facility_id,
            ).order_by(FinancialAgreement.created_at.desc()).first()
        if not agreement:
            raise HTTPException(404, "Agreement not found")
        client = db.get(Client, agreement.client_id)
        adm = db.get(Admission, agreement.admission_id) if agreement.admission_id else None
        pdf_bytes = builder.generate_agreement_pdf({
            "reference_code": agreement.reference_code,
            "version": agreement.version,
            "status": agreement.status,
            "client_name": f"{client.first_name} {client.surname}" if client else "N/A",
            "client_code": client.client_number if client else "N/A",
            "admission_code": adm.admission_number if adm else "Pre-Admission",
            "programme_name": agreement.programme_name,
            "duration_days": agreement.duration_days,
            "agreed_price": agreement.agreed_price,
            "deposit_amount": agreement.deposit_required,
            "installment_terms": agreement.installment_terms,
            "credit_terms": agreement.credit_terms,
            "inclusions": agreement.inclusions,
            "exclusions": agreement.exclusions,
            "refund_terms": agreement.refund_terms,
            "effective_date": agreement.effective_date,
        })
        service.log_export_audit("PDF", "FINANCIAL_AGREEMENT", agreement.reference_code, f"agreement_id={agreement.id}", "Print agreement")
        db.commit()
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{agreement.reference_code}_v{agreement.version}.pdf"'})

    else:
        raise HTTPException(400, f"Unsupported document type: {document_type}")


# =========================================================================
# Phase 26.6 - Sprint D: Payment Plans, Refunds & Resident Funds

# =========================================================================

@router.post("/payment-plans", response_model=PaymentPlanOut)
def create_payment_plan(
    request: Request,
    data: PaymentPlanIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.payment_plan.create"))
):
    service = FinanceService(db, request, actor)
    plan = service.create_payment_plan(data)
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/payment-plans/{plan_id}/approve", response_model=PaymentPlanOut)
def approve_payment_plan(
    request: Request,
    plan_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.payment_plan.approve"))
):
    service = FinanceService(db, request, actor)
    plan = service.approve_payment_plan(plan_id)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/payment-plans")
def list_payment_plans(
    client_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    q = db.query(PaymentPlan).filter(PaymentPlan.facility_id == actor.facility_id)
    if client_id:
        q = q.filter(PaymentPlan.client_id == client_id)
    plans = q.order_by(PaymentPlan.created_at.desc()).all()
    return {
        "items": [
            {
                "id": str(p.id),
                "client_id": str(p.client_id),
                "reference_code": p.reference_code,
                "total_amount": str(p.total_amount),
                "number_of_installments": p.number_of_installments,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in plans
        ]
    }


@router.post("/refunds", response_model=RefundOut)
def request_refund(
    request: Request,
    data: RefundRequestIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.refund.request"))
):
    service = FinanceService(db, request, actor)
    ref = service.request_refund(data)
    db.commit()
    db.refresh(ref)
    return ref


@router.post("/refunds/{refund_id}/approve", response_model=RefundOut)
def approve_refund(
    request: Request,
    refund_id: UUID,
    data: RefundApproveIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.refund.approve"))
):
    service = FinanceService(db, request, actor)
    ref = service.approve_refund(refund_id, data.approval_notes)
    db.commit()
    db.refresh(ref)
    return ref


@router.get("/refunds", response_model=list[RefundOut])
def list_refunds(
    client_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    q = db.query(Refund).filter(Refund.facility_id == actor.facility_id)
    if client_id:
        q = q.filter(Refund.client_id == client_id)
    return q.order_by(Refund.created_at.desc()).all()


@router.get("/resident-funds/client/{client_id}", response_model=ResidentFundAccountOut)
def get_resident_fund_account(
    client_id: UUID,
    admission_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("resident_funds.view"))
):
    service = FinanceService(db, None, actor)
    account = service.get_or_create_resident_fund_account(client_id, admission_id)
    db.commit()
    return account


@router.post("/resident-funds/{account_id}/deposit", response_model=ResidentFundTransactionOut)
def deposit_resident_funds(
    request: Request,
    account_id: UUID,
    data: ResidentFundDepositIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("resident_funds.deposit"))
):
    service = FinanceService(db, request, actor)
    txn = service.deposit_resident_funds(account_id, data)
    db.commit()
    db.refresh(txn)
    return txn


@router.post("/resident-funds/{account_id}/withdraw", response_model=ResidentFundTransactionOut)
def withdraw_resident_funds(
    request: Request,
    account_id: UUID,
    data: ResidentFundWithdrawIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("resident_funds.withdraw"))
):
    service = FinanceService(db, request, actor)
    txn = service.withdraw_resident_funds(account_id, data)
    db.commit()
    db.refresh(txn)
    return txn


# =========================================================================
# Phase 26.6 - Sprint E: Discharge Financial Clearance
# =========================================================================

@router.post("/discharge/{admission_id}/review", response_model=DischargeFinancialClearanceOut)
def review_discharge_clearance(
    request: Request,
    admission_id: UUID,
    data: DischargeClearanceReviewIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.discharge_clearance"))
):
    service = FinanceService(db, request, actor)
    clr = service.review_discharge_clearance(admission_id, data)
    db.commit()
    db.refresh(clr)
    return clr


@router.post("/discharge/{clearance_id}/approve", response_model=DischargeFinancialClearanceOut)
def approve_discharge_clearance(
    request: Request,
    clearance_id: UUID,
    data: DischargeClearanceApproveIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.discharge_clearance"))
):
    service = FinanceService(db, request, actor)
    clr = service.approve_discharge_clearance(clearance_id, data.notes)
    db.commit()
    db.refresh(clr)
    return clr


@router.get("/discharge/{admission_id}/clearance", response_model=DischargeFinancialClearanceOut)
def get_discharge_clearance(
    admission_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    clr = db.query(DischargeFinancialClearance).filter(
        DischargeFinancialClearance.admission_id == admission_id,
        DischargeFinancialClearance.facility_id == actor.facility_id,
    ).first()
    if not clr:
        raise HTTPException(404, "Discharge clearance record not found for admission")
    return clr


# =========================================================================
# Phase 26.6 - Sprint F: Server-Side Exports (CSV & XLSX)
# =========================================================================

def _generate_spreadsheet_export(
    rtype: str,
    fmt: str,
    filters_str: str,
    reason: str,
    db: Session,
    actor: User,
    service: FinanceService,
) -> Response:
    fmt = fmt.upper()
    rtype = rtype.upper()

    headers = []
    rows = []

    if rtype == "INVOICES":
        headers = ["Invoice Number", "Client Code", "Issue Date", "Due Date", "Status", "Subtotal", "Discount", "Tax", "Total Amount"]
        invoices = db.query(Invoice).filter(Invoice.facility_id == actor.facility_id).order_by(Invoice.issue_date.desc()).all()
        for i in invoices:
            client = db.get(Client, i.client_id)
            rows.append([
                i.invoice_number,
                client.client_number if client else "N/A",
                i.issue_date.isoformat(),
                i.due_date.isoformat(),
                i.status,
                str(i.subtotal),
                str(i.discount_amount),
                str(i.tax_amount),
                str(i.total_amount),
            ])
    elif rtype == "PAYMENTS":
        headers = ["Transaction Ref", "Client Code", "Date", "Method", "Amount", "Status"]
        payments = db.query(Payment).filter(Payment.facility_id == actor.facility_id).order_by(Payment.payment_date.desc()).all()
        for p in payments:
            client = db.get(Client, p.client_id) if p.client_id else None
            rows.append([
                p.transaction_reference,
                client.client_number if client else "N/A",
                p.payment_date.date().isoformat() if hasattr(p.payment_date, "date") else str(p.payment_date)[:10],
                p.payment_method,
                str(p.amount),
                p.status,
            ])
    elif rtype == "RESIDENT_FUNDS":
        headers = ["Account Code", "Client Code", "Balance", "Active"]
        r_accounts = db.query(ResidentFundAccount).filter(ResidentFundAccount.facility_id == actor.facility_id).all()
        for ra in r_accounts:
            client = db.get(Client, ra.client_id)
            rows.append([
                ra.reference_code,
                client.client_number if client else "N/A",
                str(ra.current_balance),
                "YES" if ra.is_active else "NO",
            ])
    elif rtype == "REFUNDS":
        headers = ["Refund Ref", "Client Code", "Amount", "Source Type", "Method", "Status"]
        refunds = db.query(Refund).filter(Refund.facility_id == actor.facility_id).all()
        for r in refunds:
            client = db.get(Client, r.client_id) if r.client_id else None
            rows.append([
                r.reference_code or str(r.id)[:8],
                client.client_number if client else "N/A",
                str(r.amount),
                r.source_type,
                r.refund_method,
                r.status,
            ])
    elif rtype == "AR_AGING":
        headers = ["Invoice Number", "Client Code", "Client Name", "Issue Date", "Due Date", "Total Amount", "Amount Paid", "Balance Due", "Aging Bucket"]
        invoices = db.query(Invoice).filter(
            Invoice.facility_id == actor.facility_id,
            Invoice.status.in_(["ISSUED", "PARTIAL", "OVERDUE", "DRAFT"])
        ).order_by(Invoice.due_date.asc()).all()
        today = date.today()
        for inv in invoices:
            client = db.get(Client, inv.client_id)
            balance_due = service.get_invoice_balance(inv.id)
            raw_allocs = db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == inv.id).scalar()
            amount_paid = money(raw_allocs) if raw_allocs is not None else Decimal("0.00")
            days_overdue = (today - inv.due_date).days
            if days_overdue <= 0:
                bucket = "Current"
            elif days_overdue <= 30:
                bucket = "1 - 30 Days"
            elif days_overdue <= 60:
                bucket = "31 - 60 Days"
            elif days_overdue <= 90:
                bucket = "61 - 90 Days"
            else:
                bucket = "90+ Days"
            rows.append([
                inv.invoice_number,
                client.client_number if client else "N/A",
                f"{client.first_name} {client.surname}" if client else "N/A",
                inv.issue_date.isoformat(),
                inv.due_date.isoformat(),
                str(inv.total_amount),
                str(amount_paid),
                str(balance_due),
                bucket,
            ])
    elif rtype == "DAILY_COLLECTIONS":
        headers = ["Transaction Ref", "Payment Date", "Client Code", "Client Name", "Payment Method", "Amount", "Status"]
        payments = db.query(Payment).filter(Payment.facility_id == actor.facility_id).order_by(Payment.payment_date.desc()).all()
        for p in payments:
            client = db.get(Client, p.client_id) if p.client_id else None
            rows.append([
                p.transaction_reference,
                p.payment_date.date().isoformat() if hasattr(p.payment_date, "date") else str(p.payment_date)[:10],
                client.client_number if client else "N/A",
                f"{client.first_name} {client.surname}" if client else "N/A",
                p.payment_method,
                str(p.amount),
                p.status,
            ])
    elif rtype == "CLIENT_BALANCES":
        headers = ["Client Code", "Client Name", "Admission Ref", "Total Invoiced", "Total Paid", "Total Credits", "Outstanding Balance", "Clearance Status"]
        clients = db.query(Client).filter(Client.facility_id == actor.facility_id).all()
        for c in clients:
            summary = service.get_client_financial_account(c.id)
            rows.append([
                c.client_number,
                f"{c.first_name} {c.surname}",
                summary.admission_number or "N/A",
                str(summary.total_charges),
                str(summary.total_payments),
                str(summary.total_credits),
                str(summary.outstanding_balance),
                summary.financial_clearance_status,
            ])
    elif rtype == "SPONSOR_BALANCES":
        headers = ["Sponsor Name", "Sponsor Code", "Contact Person", "Phone", "Email", "Active"]
        sponsors = db.query(Sponsor).filter(Sponsor.facility_id == actor.facility_id).all()
        for s in sponsors:
            rows.append([
                s.name,
                s.code,
                s.contact_person or "N/A",
                s.phone or "N/A",
                s.email or "N/A",
                "YES" if s.is_active else "NO",
            ])
    else:
        headers = ["Record ID", "Report Type", "Timestamp"]
        rows.append(["Sample", rtype, datetime.now(timezone.utc).isoformat()])

    # Log export audit
    service.log_export_audit(
        fmt, rtype, f"{rtype}_{datetime.now(timezone.utc).strftime('%Y%m%d')}", filters_str, reason
    )
    db.commit()

    if fmt == "XLSX":
        xlsx_bytes = FinancialSpreadsheetExporter.export_to_xlsx(rtype, headers, rows)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{rtype.lower()}_export.xlsx"'},
        )
    else:
        csv_str = FinancialSpreadsheetExporter.export_to_csv(headers, rows)
        return Response(
            content=csv_str.encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{rtype.lower()}_export.csv"'},
        )


@router.post("/export")
def export_finance_report(
    request: Request,
    data: BillingExportRequestIn,
    db: Session = Depends(get_db),
    actor=Depends(require_any_permission("billing.export", "finance.export"))
):
    service = FinanceService(db, request, actor)
    return _generate_spreadsheet_export(
        rtype=data.report_type,
        fmt=data.export_format,
        filters_str=str(data.filters),
        reason=data.reason,
        db=db,
        actor=actor,
        service=service,
    )


@router.get("/exports/spreadsheet")
def export_spreadsheet_get(
    report_type: str,
    export_format: str = "CSV",
    request: Request = None,
    db: Session = Depends(get_db),
    actor=Depends(require_any_permission("billing.export", "finance.export"))
):
    service = FinanceService(db, request, actor)
    return _generate_spreadsheet_export(
        rtype=report_type,
        fmt=export_format,
        filters_str=f"report_type={report_type}",
        reason="Client Finance Workspace export",
        db=db,
        actor=actor,
        service=service,
    )


