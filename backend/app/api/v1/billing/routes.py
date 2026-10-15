"""Billing and financial API routes."""

from datetime import datetime
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
from app.models.billing import (
    Invoice, Payment, Payer, BillingService, MpesaTransaction,
    CreditNote, Refund, WriteOff, Adjustment, PaymentAllocation
)
from app.schemas.billing import (
    InvoiceIn, InvoiceOut, PaymentIn, PaymentOut, 
    PayerIn, PayerOut, BillingServiceIn, BillingServiceOut,
    StkPushIn, ManualAllocationIn, MpesaTransactionOut
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
    query = db.query(Invoice)
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if status:
        query = query.filter(Invoice.status == status)
    
    total = query.count()
    limit = 20
    items = query.order_by(Invoice.issue_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Simple dict return since InvoiceOut might have relationships we didn't eagerly load
    # In a full implementation, you'd use a service method that properly constructs InvoiceOut with items
    return {
        "items": [
            {
                "id": str(i.id),
                "client_id": str(i.client_id),
                "invoice_number": i.invoice_number,
                "status": i.status,
                "total_amount": float(i.total_amount),
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
    return service.create_invoice(invoice)


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
        
    return service.record_payment(payment, allocations)

@router.get("/payments")
def get_payments(
    request: Request,
    page: int = 1,
    client_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    query = db.query(Payment)
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
                "amount": float(i.amount),
                "payment_method": i.payment_method,
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
    query = db.query(Payer)
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
                "contact_phone": i.contact_phone
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/payers", response_model=PayerOut)
def create_payer(
    payer: PayerIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    db_payer = Payer(**payer.model_dump(), facility_id=actor.facility_id)
    db.add(db_payer)
    db.commit()
    db.refresh(db_payer)
    return db_payer

@router.get("/services")
def get_services(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    query = db.query(BillingService)
    total = query.count()
    limit = 20
    items = query.order_by(BillingService.name.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": str(i.id),
                "code": i.code,
                "name": i.name,
                "category": i.category
            } for i in items
        ],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/services", response_model=BillingServiceOut)
def create_service(
    service: BillingServiceIn,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    db_service = BillingService(**service.model_dump(), facility_id=actor.facility_id)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.post("/mpesa/stk-push", response_model=MpesaTransactionOut, tags=["M-Pesa"])
def initiate_mpesa_stk_push(
    payload: StkPushIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.collect_payment")),
):
    """Initiate an M-Pesa Daraja STK Push prompt on client's phone."""
    service = MpesaService(db, actor=actor, request=request)
    return service.initiate_stk_push(
        facility_id=actor.facility_id,
        client_id=payload.client_id,
        invoice_id=payload.invoice_id,
        phone_number=payload.phone_number,
        amount=payload.amount,
    )


@router.post("/mpesa/callback", tags=["M-Pesa"])
async def mpesa_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """Public callback endpoint for Safaricom Daraja STK Push notifications."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    service = MpesaService(db, request=request)
    return service.process_callback(body)


@router.post("/mpesa/webhook", tags=["M-Pesa"])
async def mpesa_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Public webhook endpoint for Safaricom C2B / Paybill transactions."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    service = MpesaService(db, request=request)
    return service.process_callback(body)


@router.get("/mpesa/reconciliation", tags=["M-Pesa"])
def get_mpesa_reconciliation_list(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    reconciliation_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view")),
):
    """Workspace listing for M-Pesa transactions, auto-reconciliation, and manual allocation."""
    query = db.query(MpesaTransaction).filter(MpesaTransaction.facility_id == actor.facility_id)

    if status:
        query = query.filter(MpesaTransaction.status == status)
    if reconciliation_status:
        query = query.filter(MpesaTransaction.reconciliation_status == reconciliation_status)
    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            or_(
                MpesaTransaction.transaction_reference.ilike(search_filter),
                MpesaTransaction.phone_number.ilike(search_filter),
                MpesaTransaction.merchant_request_id.ilike(search_filter),
                MpesaTransaction.checkout_request_id.ilike(search_filter),
            )
        )

    total = query.count()
    items = (
        query.order_by(MpesaTransaction.timestamp.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "items": [
            {
                "id": str(tx.id),
                "facility_id": str(tx.facility_id),
                "transaction_reference": tx.transaction_reference,
                "phone_number": tx.phone_number,
                "amount": float(tx.amount),
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
            "pages": math.ceil(total / limit) if limit else 1,
        },
    }


@router.post("/mpesa/reconciliation/{transaction_id}/allocate", response_model=MpesaTransactionOut, tags=["M-Pesa"])
def manually_allocate_mpesa(
    transaction_id: UUID,
    payload: ManualAllocationIn,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("finance.reconcile")),
):
    """Manually allocate an unmatched or manual-review M-Pesa transaction to an invoice."""
    service = MpesaService(db, actor=actor, request=request)
    return service.allocate_unmatched_transaction(
        transaction_id=transaction_id,
        invoice_id=payload.invoice_id,
        notes=payload.notes or "",
    )



@router.get("/statements/{client_id}")
def get_client_statement(
    client_id: UUID,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.view"))
):
    invoices = db.query(Invoice).filter(Invoice.client_id == client_id).all()
    payments = db.query(Payment).filter(Payment.client_id == client_id).all()
    
    total_invoiced = sum(i.total_amount for i in invoices if i.status != "CANCELLED")
    total_paid = sum(p.amount for p in payments if p.status == "COMPLETED")
    
    # Simple debt ageing
    now = datetime.utcnow().date()
    ageing = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    
    for inv in invoices:
        if inv.status in ("PAID", "CANCELLED", "WRITTEN_OFF"):
            continue
            
        allocs = db.query(db.func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == inv.id).scalar() or 0
        balance = float(inv.total_amount) - float(allocs)
        
        if balance > 0 and inv.due_date:
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
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "outstanding_balance": total_invoiced - total_paid,
        "ageing": ageing,
        "invoices": [{"id": str(i.id), "number": i.invoice_number, "date": i.issue_date, "amount": i.total_amount, "status": i.status} for i in invoices],
        "payments": [{"id": str(p.id), "date": p.payment_date, "amount": p.amount, "method": p.payment_method} for p in payments]
    }


@router.post("/adjustments")
def create_adjustment(
    invoice_id: UUID,
    amount: float,
    reason: str,
    adjustment_type: str,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    service = FinanceService(db, request, actor)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
        
    adj = Adjustment(
        facility_id=actor.facility_id,
        invoice_id=invoice_id,
        amount=amount,
        reason=reason,
        adjustment_type=adjustment_type,
        created_by=actor.id
    )
    db.add(adj)
    
    # Adjust total
    invoice.total_amount = float(invoice.total_amount) + amount
    db.commit()
    service.event("billing.adjustment_created", adj)
    return {"message": "Adjustment created", "new_total": invoice.total_amount}


@router.post("/writeoffs")
def create_writeoff(
    invoice_id: UUID,
    amount: float,
    reason: str,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(require_permission("billing.edit"))
):
    service = FinanceService(db, request, actor)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
        
    wo = WriteOff(
        facility_id=actor.facility_id,
        invoice_id=invoice_id,
        amount=amount,
        reason=reason,
        approved_by=actor.id,
        written_off_at=datetime.utcnow()
    )
    db.add(wo)
    
    # Recheck status after write-off
    allocs = db.query(db.func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == invoice_id).scalar() or 0
    if float(allocs) + float(amount) >= float(invoice.total_amount):
        invoice.status = "WRITTEN_OFF"
        
    # Post to General Ledger: Dr Bad Debt (6000) / Cr Accounts Receivable (1200)
    try:
        from app.services.finance import FinanceLedgerService
        ledger = FinanceLedgerService(db, request, actor)
        wo_amt = Decimal(str(amount))
        ledger.post_journal(
            entry_date=datetime.utcnow().date(),
            reference=f"WO-{str(wo.id)[:8]}",
            description=f"Write-off for invoice {invoice.invoice_number}: {reason}",
            source_module="BILLING_WRITEOFF",
            source_id=str(wo.id),
            posting_type="WRITEOFF",
            lines=[
                {"account_code": "6000", "debit": wo_amt, "credit": 0},
                {"account_code": "1200", "debit": 0, "credit": wo_amt},
            ],
        )
    except Exception as exc:
        pass

    db.commit()
    service.event("billing.writeoff_created", wo)
    return {"message": "Write-off created", "status": invoice.status}
