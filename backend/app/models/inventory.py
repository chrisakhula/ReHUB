"""Inventory and stores models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class Supplier(Record, Base):
    __tablename__ = "inventory_suppliers"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    contact_person: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StoreItem(Record, Base):
    __tablename__ = "inventory_store_items"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100)) # e.g. MEDICAL, FOOD, CLEANING, OFFICE
    unit_of_measure: Mapped[str] = mapped_column(String(50)) # e.g. BOX, PIECE, LITER, KG
    
    current_stock: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    reorder_level: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PurchaseOrder(Record, Base):
    __tablename__ = "inventory_purchase_orders"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_suppliers.id"))
    order_number: Mapped[str] = mapped_column(String(100), unique=True)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT") # DRAFT, APPROVED, ORDERED, RECEIVED, CANCELLED
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    requested_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class StockTransaction(Record, Base):
    __tablename__ = "inventory_stock_transactions"
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_store_items.id"))
    transaction_type: Mapped[str] = mapped_column(String(50)) # RECEIPT, ISSUE, ADJUSTMENT, RETURN
    quantity: Mapped[float] = mapped_column(Numeric(10, 2))
    batch_number: Mapped[str] = mapped_column(String(100), default="")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference: Mapped[str] = mapped_column(String(200), default="") # PO number, Request ID
    performed_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str] = mapped_column(Text, default="")
