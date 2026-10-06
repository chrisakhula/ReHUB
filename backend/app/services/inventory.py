"""Inventory service layer."""

from uuid import UUID
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.audit.events import audit
from app.models.inventory import (
    Supplier,
    StoreItem,
    PurchaseOrder,
    StockTransaction,
)
from app.schemas.inventory import (
    SupplierIn,
    StoreItemIn,
    PurchaseOrderIn,
    StockTransactionIn,
)
from app.models.identity import User


class InventoryService:
    def __init__(self, db: Session, request: Request, actor: User):
        self.db = db
        self.request = request
        self.actor = actor

    def event(self, action: str, entity, new: dict = None, previous: dict = None, reason: str = ""):
        audit(self.db, self.request, action, entity.__class__.__name__, self.actor, getattr(entity, "id", None))

    def create_supplier(self, data: SupplierIn) -> Supplier:
        supplier = Supplier(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        self.event("inventory.supplier_created", supplier)
        return supplier

    def create_store_item(self, data: StoreItemIn) -> StoreItem:
        item = StoreItem(
            **data.model_dump(),
            facility_id=self.actor.facility_id
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        self.event("inventory.store_item_created", item)
        return item

    def create_purchase_order(self, data: PurchaseOrderIn) -> PurchaseOrder:
        po = PurchaseOrder(
            **data.model_dump(),
            facility_id=self.actor.facility_id,
            requested_by_id=self.actor.id
        )
        self.db.add(po)
        self.db.commit()
        self.db.refresh(po)
        self.event("inventory.purchase_order_created", po)
        return po

    def update_po_status(self, po_id: UUID, status: str) -> PurchaseOrder:
        po = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            raise HTTPException(404, "Purchase Order not found")
            
        po.status = status
        if status == "APPROVED":
            po.approved_by_id = self.actor.id
            
        self.db.commit()
        self.db.refresh(po)
        self.event(f"inventory.purchase_order_status_{status.lower()}", po)
        return po

    def record_transaction(self, data: StockTransactionIn) -> StockTransaction:
        item = self.db.query(StoreItem).filter(StoreItem.id == data.item_id).first()
        if not item:
            raise HTTPException(404, "Store item not found")
            
        transaction = StockTransaction(
            **data.model_dump(),
            facility_id=self.actor.facility_id,
            performed_by_id=self.actor.id
        )
        self.db.add(transaction)
        
        # Adjust stock level
        if data.transaction_type in ("RECEIPT", "RETURN"):
            item.current_stock = float(item.current_stock) + data.quantity
        elif data.transaction_type == "ISSUE":
            if item.current_stock < data.quantity:
                raise HTTPException(400, "Insufficient stock")
            item.current_stock = float(item.current_stock) - data.quantity
        elif data.transaction_type == "ADJUSTMENT":
            # adjustment logic could be replacement or relative. Assuming absolute replacement for simplicity
            item.current_stock = data.quantity
            
        self.db.commit()
        self.db.refresh(transaction)
        self.event("inventory.stock_transaction_recorded", transaction)
        return transaction
