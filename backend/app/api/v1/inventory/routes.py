from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import math
from app.core.database import get_db
from app.models.inventory import InventoryItem
from app.schemas.inventory import InventoryItemCreate, InventoryItemResponse

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("/items")
def get_inventory_items(
    page: int = 1,
    q: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(InventoryItem)
    if q:
        query = query.filter(InventoryItem.name.ilike(f"%{q}%"))
    
    total = query.count()
    limit = 20
    items = query.order_by(InventoryItem.name.asc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [InventoryItemResponse.model_validate(i).model_dump() for i in items],
        "meta": {"total": total, "page": page, "pages": math.ceil(total / limit)}
    }

@router.post("/items")
def create_item(item: InventoryItemCreate, db: Session = Depends(get_db)):
    db_item = InventoryItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return InventoryItemResponse.model_validate(db_item).model_dump()
