from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict
from enum import Enum

class ItemCategory(str, Enum):
    MEDICATION = "medication"
    CONSUMABLE = "consumable"
    EQUIPMENT = "equipment"
    FOOD = "food"
    OFFICE = "office"

class InventoryItemBase(BaseModel):
    name: str
    category: ItemCategory
    unit_of_measure: str
    minimum_stock_level: int = 0
    current_stock: int = 0
    reorder_quantity: int = 0
    model_config = ConfigDict(from_attributes=True)

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemResponse(InventoryItemBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
