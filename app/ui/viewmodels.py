"""Lightweight view models shared by the UI layer."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MenuItemInfo:
    """Snapshot of a menu item used by the presentation layer."""

    id: int
    name: str
    price_cents: int
    category_id: int
    image_path: Optional[str] = None
