"""Inventory API routes."""

import math
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.inventory import Supplier, StoreItem, PurchaseOrder, StockTransaction
from app.schemas.inventory import (
    SupplierIn, SupplierOut,
    StoreItemIn, StoreItemOut,
    PurchaseOrderIn, PurchaseOrderOut,
    StockTransactionIn, StockTransactionOut,
)
from app.services.inventory import InventoryService


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
    dependencies=[Depends(require_permission("inventory.view"))]
)

@router.get("/items")
def get_store_items(page: int = 1, db: Session = Depends(get_db), actor=Depends(require_permission("inventory.view"))):
    query = db.query(StoreItem).filter(StoreItem.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(StoreItem.name.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [{"id": str(i.id), "code": i.code, "name": i.name, "category": i.category, "current_stock": i.current_stock, "unit_of_measure": i.unit_of_measure} for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/items", response_model=StoreItemOut)
def create_store_item(request: Request, item: StoreItemIn, db: Session = Depends(get_db), actor=Depends(require_permission("inventory.edit"))):
    service = InventoryService(db, request, actor)
    return service.create_store_item(item)

@router.get("/suppliers")
def get_suppliers(page: int = 1, db: Session = Depends(get_db), actor=Depends(require_permission("inventory.view"))):
    query = db.query(Supplier).filter(Supplier.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(Supplier.name.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [{"id": str(i.id), "name": i.name, "contact_person": i.contact_person, "phone": i.phone} for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(request: Request, supplier: SupplierIn, db: Session = Depends(get_db), actor=Depends(require_permission("inventory.edit"))):
    service = InventoryService(db, request, actor)
    return service.create_supplier(supplier)

@router.get("/orders")
def get_purchase_orders(page: int = 1, db: Session = Depends(get_db), actor=Depends(require_permission("inventory.view"))):
    query = db.query(PurchaseOrder).filter(PurchaseOrder.facility_id == actor.facility_id)
    total = query.count()
    limit = 20
    items = query.order_by(PurchaseOrder.order_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [{"id": str(i.id), "order_number": i.order_number, "order_date": i.order_date.isoformat() if i.order_date else None, "status": i.status, "total_amount": i.total_amount} for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit) if limit else 1}
    }

@router.post("/orders", response_model=PurchaseOrderOut)
def create_purchase_order(request: Request, po: PurchaseOrderIn, db: Session = Depends(get_db), actor=Depends(require_permission("inventory.edit"))):
    service = InventoryService(db, request, actor)
    return service.create_purchase_order(po)

@router.post("/transactions", response_model=StockTransactionOut)
def record_transaction(request: Request, transaction: StockTransactionIn, db: Session = Depends(get_db), actor=Depends(require_permission("inventory.edit"))):
    service = InventoryService(db, request, actor)
    return service.record_transaction(transaction)
