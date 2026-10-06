from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
import math
from app.core.database import get_db
from app.models.billing import Invoice
from app.schemas.billing import InvoiceCreate, InvoiceResponse

router = APIRouter(prefix="/billing", tags=["Billing"])

@router.get("/invoices")
def get_invoices(
    page: int = 1,
    q: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Invoice)
    if status:
        query = query.filter(Invoice.status == status)
    
    total = query.count()
    limit = 20
    items = query.order_by(Invoice.issue_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [InvoiceResponse.model_validate(i).model_dump() for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit)}
    }

@router.post("/invoices")
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    db_invoice = Invoice(**invoice.model_dump())
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return InvoiceResponse.model_validate(db_invoice).model_dump()
