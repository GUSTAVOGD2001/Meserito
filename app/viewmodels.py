"""Pydantic models bridging SQLAlchemy entities and PyQt views."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class OrmViewModel(BaseModel):
    """Base class for models built from SQLAlchemy entities."""

    class Config:
        from_attributes = True


class MenuItemInfo(OrmViewModel):
    """Serializable snapshot of a menu item."""

    id: int
    name: str
    price_cents: int
    category_id: int
    description: Optional[str] = None
    image_path: Optional[str] = None


class WaiterInfo(OrmViewModel):
    """Details required to identify and authenticate a waiter."""

    id: int
    name: str
    pin: str
    is_manager: bool
    is_active: bool


class TableInfo(OrmViewModel):
    """Table information shared between the UI and persistence layers."""

    id: int
    number: int
    name: Optional[str] = None
    capacity: int
    status: str


class OrderInfo(OrmViewModel):
    """Order summary exposed to the presentation layer."""

    id: int
    table_id: int
    waiter_id: int
    covers: int
    status: str
    subtotal_cents: int
    tax_cents: int
    total_cents: int
