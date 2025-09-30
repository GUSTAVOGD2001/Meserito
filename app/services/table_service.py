"""Table service for managing restaurant floor tables."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..event_bus import event_bus
from ..models import Order, Table
from .exceptions import DomainError


class TableService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_tables(self) -> list[Table]:
        stmt = select(Table).order_by(Table.number)
        return list(self.session.scalars(stmt))

    def get_table(self, table_id: int) -> Table:
        table = self.session.get(Table, table_id)
        if not table:
            raise DomainError("Mesa no encontrada")
        return table

    def create_table(self, *, number: int, x: int = 0, y: int = 0, capacity: int = 2, name: Optional[str] = None) -> Table:
        table = Table(number=number, x=x, y=y, capacity=capacity, name=name)
        self.session.add(table)
        self.session.flush()
        return table

    def update_table(self, table_id: int, **kwargs) -> Table:
        table = self.get_table(table_id)
        for field in ("number", "x", "y", "capacity", "name", "status"):
            if field in kwargs:
                setattr(table, field, kwargs[field])
        self.session.flush()
        return table

    def delete_table(self, table_id: int) -> None:
        table = self.get_table(table_id)
        if table.current_order_id:
            raise DomainError("No se puede eliminar una mesa con un pedido activo")
        self.session.delete(table)

    def open_order(self, table_id: int, waiter_id: int, covers: int) -> Order:
        table = self.get_table(table_id)
        if table.current_order_id:
            raise DomainError("La mesa ya tiene un pedido abierto")
        order = Order(table_id=table.id, waiter_id=waiter_id, covers=covers)
        self.session.add(order)
        self.session.flush()

        table.current_order_id = order.id
        table.status = "active" if not order.items else "occupied"
        event_bus.publish("table_status_changed", {"table_id": table.id, "status": table.status})
        return order

    def close_order(self, table_id: int) -> Order:
        table = self.get_table(table_id)
        if not table.current_order_id:
            raise DomainError("La mesa no tiene un pedido activo")
        order = self.session.get(Order, table.current_order_id)
        if not order:
            raise DomainError("Pedido no encontrado")
        order.status = "closed"
        order.closed_at = datetime.utcnow()
        table.current_order_id = None
        table.status = "free"
        self.session.flush()
        event_bus.publish("table_status_changed", {"table_id": table.id, "status": table.status})
        return order

    def mark_occupied(self, table_id: int) -> None:
        table = self.get_table(table_id)
        table.status = "occupied"
        self.session.flush()
        event_bus.publish("table_status_changed", {"table_id": table.id, "status": table.status})
