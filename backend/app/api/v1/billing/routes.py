"""Billing and financial API routes."""

from uuid import UUID
from typing import Optional
import math

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.billing import Invoice, Payment, Payer, BillingService
from app.schemas.billing import (
    InvoiceIn, InvoiceOut, PaymentIn, PaymentOut, 
    PayerIn, PayerOut, BillingServiceIn, BillingServiceOut
)
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
