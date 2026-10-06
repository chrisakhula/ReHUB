"""Billing and financial API routes."""

from uuid import UUID
from typing import Optional
import math

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.billing import (
    Invoice, Payment, Payer, BillingService, MpesaTransaction,
    CreditNote, Refund, WriteOff, Adjustment, PaymentAllocation
)
from app.schemas.billing import (
    InvoiceIn, InvoiceOut, PaymentIn, PaymentOut, 
    PayerIn, PayerOut, BillingServiceIn, BillingServiceOut
)
from datetime import datetime
from pydantic import BaseModel
from app.services.billing import FinanceService


router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
    dependencies=[Depends(require_permission("billing.view"))]
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

class MpesaPayload(BaseModel):
    TransID: str
    TransAmount: str
    MSISDN: str
    TransTime: str
    BillRefNumber: Optional[str] = None

@router.post("/mpesa/webhook", tags=["Integration"])
def mpesa_webhook(
    payload: MpesaPayload,
    request: Request,
    db: Session = Depends(get_db)
):
    # This endpoint typically doesn't use the standard actor permissions 
    # since it is called by Safaricom externally. 
    # It would be protected by an IP whitelist or a specific secret token.
    # We use a system actor or bypass the standard actor requirement for this specific route.
    
    # 1. Parse payload
    timestamp_str = payload.TransTime
    dt = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S") if timestamp_str else datetime.utcnow()
    
    # 2. Record Transaction
    tx = MpesaTransaction(
        facility_id=UUID("00000000-0000-0000-0000-000000000000"), # Needs resolution to actual facility
        transaction_reference=payload.TransID,
        phone_number=payload.MSISDN,
        amount=float(payload.TransAmount),
        timestamp=dt,
        status="PENDING",
        raw_payload=payload.model_dump_json()
    )
    db.add(tx)
    
    # 3. Attempt Auto-Reconciliation based on BillRefNumber (e.g. Invoice Number or Client Number)
    if payload.BillRefNumber:
        invoice = db.query(Invoice).filter(Invoice.invoice_number == payload.BillRefNumber).first()
        if invoice and invoice.status not in ("PAID", "CANCELLED", "WRITTEN_OFF"):
            tx.invoice_id = invoice.id
            tx.payer_id = invoice.payer_id
            # Creating a payment record automatically
            payment = Payment(
                facility_id=invoice.facility_id,
                payer_id=invoice.payer_id,
                client_id=invoice.client_id,
                amount=float(payload.TransAmount),
                payment_method="MPESA",
                transaction_reference=payload.TransID,
                payment_date=dt,
                status="COMPLETED"
            )
            db.add(payment)
            db.flush()
            
            # Allocate to invoice
            alloc = PaymentAllocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount=float(payload.TransAmount),
                allocated_at=dt,
                allocated_by=UUID("00000000-0000-0000-0000-000000000000") # System user
            )
            db.add(alloc)
            
            tx.reconciled_payment_id = payment.id
            tx.status = "RECONCILED"
            
            # Update invoice status
            total_allocated = db.query(db.func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == invoice.id).scalar() or 0
            if total_allocated + float(payload.TransAmount) >= invoice.total_amount:
                invoice.status = "PAID"
            else:
                invoice.status = "PARTIAL"

    db.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


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
    if allocs + amount >= invoice.total_amount:
        invoice.status = "WRITTEN_OFF"
        
    db.commit()
    service.event("billing.writeoff_created", wo)
    return {"message": "Write-off created", "status": invoice.status}
