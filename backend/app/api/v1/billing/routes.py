"""Billing and financial API routes."""

from datetime import datetime, timezone
from decimal import Decimal
import math
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.money import money
from app.models.billing import (
    Invoice, Payment, Payer, BillingService, MpesaTransaction,
    CreditNote, Refund, WriteOff, Adjustment, PaymentAllocation
)
from app.schemas.billing import (
    InvoiceIn, InvoiceOut, PaymentIn, PaymentOut, 
    PayerIn, PayerOut, BillingServiceIn, BillingServiceOut,
    StkPushIn, ManualAllocationIn, MpesaTransactionOut,
    CreditNoteIn, CreditNoteOut, CreditNoteApproveIn,
    WriteOffIn, WriteOffOut, WriteOffApproveIn
)
from app.services.billing import FinanceService
from app.services.mpesa import MpesaService


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
