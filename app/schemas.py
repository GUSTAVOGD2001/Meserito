"""Pydantic schemas for Meserito services."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class WaiterSchema(BaseModel):
    id: int
    name: str
    pin: str
    is_active: bool
    is_manager: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TableSchema(BaseModel):
    id: int
    number: int
    name: Optional[str]
    x: int
    y: int
    capacity: int
    status: str
    current_order_id: Optional[int]

    class Config:
        from_attributes = True


class MenuItemSchema(BaseModel):
    id: int
    category_id: int
    name: str
    price_cents: int
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class OrderItemSchema(BaseModel):
    id: int
    order_id: int
    menu_item_id: int
    qty: int
    unit_price_cents: int
    notes: Optional[str]
    status: str

    class Config:
        from_attributes = True


class OrderSchema(BaseModel):
    id: int
    table_id: int
    waiter_id: int
    covers: int
    opened_at: datetime
    closed_at: Optional[datetime]
    status: str
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    items: List[OrderItemSchema] = []

    class Config:
        from_attributes = True
