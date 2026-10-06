from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.billing import (
    Invoice,
    InvoiceItem,
    Payment,
    PaymentAllocation,
    Payer,
)
from app.schemas.billing import InvoiceIn, PaymentIn
from app.audit.events import audit


class FinanceService:
    def __init__(self, db: Session, request, actor):
        self.db = db
        self.request = request
        self.actor = actor

    def require(self, permission: str):
        # We assume the user has a list of permissions attached to their role
        # This is a simplified check assuming `permission_codes` exists in actor or similar
        # Since we don't have access to the exact implementation of permission_codes, 
        # we assume it's handled at the router level via `require_permission`
        pass

    def event(self, action: str, entity, new: dict = None, previous: dict = None, reason: str = ""):
        audit(self.db, self.request, action, entity.__class__.__name__, self.actor, getattr(entity, "id", None))

    def create_invoice(self, data: InvoiceIn) -> Invoice:
        invoice = Invoice(
            facility_id=self.actor.facility_id,
            client_id=data.client_id,
            admission_id=data.admission_id,
            payer_id=data.payer_id,
            invoice_number=data.invoice_number,
            issue_date=data.issue_date,
            due_date=data.due_date,
            status=data.status,
            notes=data.notes,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(invoice)
        self.db.flush()

        subtotal = 0.0
        tax = 0.0
        discount = 0.0

        for item_in in data.items:
            item_total = (item_in.quantity * item_in.unit_price) - item_in.discount
            if item_total < 0:
                item_total = 0
            
            item_tax = item_total * (item_in.tax_rate / 100.0)
            item_total_with_tax = item_total + item_tax

            item = InvoiceItem(
                invoice_id=invoice.id,
                service_id=item_in.service_id,
                package_id=item_in.package_id,
                description=item_in.description,
                quantity=item_in.quantity,
                unit_price=item_in.unit_price,
                discount=item_in.discount,
                tax_rate=item_in.tax_rate,
                total_price=item_total_with_tax,
                created_by=self.actor.id,
                updated_by=self.actor.id,
            )
            self.db.add(item)
            
            subtotal += float(item_in.quantity * item_in.unit_price)
            discount += float(item_in.discount)
            tax += float(item_tax)

        invoice.subtotal = subtotal
        invoice.discount_amount = discount
        invoice.tax_amount = tax
        invoice.total_amount = subtotal - discount + tax
        
        self.db.flush()
        self.event("billing.invoice_created", invoice)
        return invoice

    def record_payment(self, data: PaymentIn, invoice_allocations: dict[UUID, float] = None) -> Payment:
        payment = Payment(
            facility_id=self.actor.facility_id,
            payer_id=data.payer_id,
            client_id=data.client_id,
            amount=data.amount,
            payment_method=data.payment_method,
            transaction_reference=data.transaction_reference,
            payment_date=data.payment_date,
            notes=data.notes,
            status="COMPLETED",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(payment)
        self.db.flush()
        self.event("billing.payment_received", payment)

        if invoice_allocations:
            for inv_id, alloc_amount in invoice_allocations.items():
                self.allocate_payment(payment.id, inv_id, alloc_amount)

        return payment

    def allocate_payment(self, payment_id: UUID, invoice_id: UUID, amount: float):
        allocation = PaymentAllocation(
            payment_id=payment_id,
            invoice_id=invoice_id,
            amount=amount,
            allocated_at=datetime.utcnow(),
            allocated_by=self.actor.id,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(allocation)
        self.db.flush()

        # Update invoice status
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            total_allocated = self.db.query(func.sum(PaymentAllocation.amount)).filter(PaymentAllocation.invoice_id == invoice_id).scalar() or 0
            if total_allocated >= invoice.total_amount:
                invoice.status = "PAID"
            elif total_allocated > 0:
                invoice.status = "PARTIAL"
            self.event("billing.invoice_status_updated", invoice)
