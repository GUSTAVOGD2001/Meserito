"""Menu related operations."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Category, MenuItem
from .exceptions import ValidationError


class MenuService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # Category operations
    def list_categories(self, active_only: bool = True) -> List[Category]:
        stmt = select(Category)
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        return list(self.session.scalars(stmt.order_by(Category.sort_order, Category.name)))

    def create_category(self, name: str, sort_order: int = 0, is_active: bool = True) -> Category:
        if not name:
            raise ValidationError("El nombre de la categoría es obligatorio")
        category = Category(name=name, sort_order=sort_order, is_active=is_active)
        self.session.add(category)
        self.session.flush()
        return category

    def update_category(self, category_id: int, **kwargs) -> Category:
        category = self.session.get(Category, category_id)
        if not category:
            raise ValidationError("Categoría no encontrada")
        for field in ("name", "sort_order", "is_active"):
            if field in kwargs:
                setattr(category, field, kwargs[field])
        self.session.flush()
        return category

    def delete_category(self, category_id: int) -> None:
        category = self.session.get(Category, category_id)
        if not category:
            raise ValidationError("Categoría no encontrada")
        self.session.delete(category)

    # Menu items
    def list_items(self, category_id: Optional[int] = None, include_inactive: bool = False) -> List[MenuItem]:
        stmt = select(MenuItem)
        if category_id is not None:
            stmt = stmt.where(MenuItem.category_id == category_id)
        if not include_inactive:
            stmt = stmt.where(MenuItem.is_active.is_(True))
        stmt = stmt.order_by(MenuItem.name)
        return list(self.session.scalars(stmt))

    def search_items(self, text: str) -> List[MenuItem]:
        stmt = (
            select(MenuItem)
            .where(MenuItem.is_active.is_(True), MenuItem.name.ilike(f"%{text}%"))
            .order_by(MenuItem.name)
        )
        return list(self.session.scalars(stmt))

    def create_item(
        self,
        *,
        category_id: int,
        name: str,
        price_cents: int,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> MenuItem:
        if price_cents < 0:
            raise ValidationError("El precio no puede ser negativo")
        item = MenuItem(
            category_id=category_id,
            name=name,
            price_cents=price_cents,
            description=description,
            is_active=is_active,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def update_item(self, item_id: int, **kwargs) -> MenuItem:
        item = self.session.get(MenuItem, item_id)
        if not item:
            raise ValidationError("Platillo no encontrado")
        for field in ("name", "price_cents", "description", "is_active", "category_id"):
            if field in kwargs and kwargs[field] is not None:
                if field == "price_cents" and kwargs[field] < 0:
                    raise ValidationError("El precio no puede ser negativo")
                setattr(item, field, kwargs[field])
        self.session.flush()
        return item

    def deactivate_item(self, item_id: int) -> MenuItem:
        return self.update_item(item_id, is_active=False)

    def activate_item(self, item_id: int) -> MenuItem:
        return self.update_item(item_id, is_active=True)
