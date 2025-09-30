"""Order service encapsulating order workflows."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..event_bus import event_bus
from ..models import AuditLog, MenuItem, Order, OrderItem, Setting
from .exceptions import DomainError, ValidationError


DEFAULT_TAX_PERCENT = Decimal("16.0")


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_order(self, order_id: int) -> Order:
        order = self.session.get(Order, order_id)
        if not order:
            raise DomainError("Pedido no encontrado")
        return order

    def get_or_create_open_order(self, table_id: int, waiter_id: int, covers: int) -> Order:
        stmt = select(Order).where(Order.table_id == table_id, Order.status == "open")
        order = self.session.scalars(stmt).first()
        if order:
            return order
        order = Order(table_id=table_id, waiter_id=waiter_id, covers=covers)
        self.session.add(order)
        self.session.flush()
        event_bus.publish("order_updated", {"order_id": order.id})
        return order

    def add_item(self, order_id: int, menu_item_id: int, qty: int, notes: Optional[str] = None) -> OrderItem:
        if qty <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero")
        order = self.get_order(order_id)
        if order.status != "open":
            raise DomainError("Solo se pueden agregar ítems a pedidos abiertos")
        menu_item = self.session.get(MenuItem, menu_item_id)
        if not menu_item or not menu_item.is_active:
            raise ValidationError("El platillo no está disponible")
        item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            qty=qty,
            unit_price_cents=menu_item.price_cents,
            notes=notes,
        )
        self.session.add(item)
        self.session.flush()
        event_bus.publish("order_updated", {"order_id": order.id})
        return item

    def update_item_qty(self, item_id: int, qty: int) -> OrderItem:
        if qty < 0:
            raise ValidationError("Cantidad inválida")
        item = self.session.get(OrderItem, item_id)
        if not item:
            raise DomainError("Ítem no encontrado")
        if item.order.status != "open":
            raise DomainError("Solo se pueden modificar pedidos abiertos")
        item.qty = qty
        self.session.flush()
        event_bus.publish("order_updated", {"order_id": item.order_id})
        return item

    def void_item(self, item_id: int, reason: str) -> OrderItem:
        item = self.session.get(OrderItem, item_id)
        if not item:
            raise DomainError("Ítem no encontrado")
        item.status = "void"
        item.notes = (item.notes or "") + f"\nAnulado: {reason}"
        log = AuditLog(
            actor_type="system",
            action="void_item",
            entity="order_item",
            entity_id=item.id,
            payload_json=reason,
        )
        self.session.add(log)
        self.session.flush()
        event_bus.publish("order_updated", {"order_id": item.order_id})
        return item

    def compute_totals(self, order_id: int, tax_rate_setting_key: str = "tax_rate_percent") -> Order:
        order = self.get_order(order_id)
        subtotal = 0
        for item in order.items:
            if item.status != "void":
                subtotal += item.qty * item.unit_price_cents
        tax_percent = self._get_tax_percent(tax_rate_setting_key)
        tax = int(round(subtotal * (tax_percent / Decimal(100))))
        total = subtotal + tax
        order.subtotal_cents = subtotal
        order.tax_cents = tax
        order.total_cents = total
        self.session.flush()
        event_bus.publish("order_updated", {"order_id": order.id})
        return order

    def _get_tax_percent(self, key: str) -> Decimal:
        setting = self.session.get(Setting, key)
        if not setting:
            return DEFAULT_TAX_PERCENT
        try:
            return Decimal(setting.value)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValidationError("Configuración de impuesto inválida") from exc
