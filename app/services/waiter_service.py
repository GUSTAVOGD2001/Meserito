"""Service helpers for employee management."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Waiter
from .exceptions import ValidationError


class WaiterService:
    """CRUD utilities for managing restaurant employees."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_waiters(self, include_managers: bool = True) -> List[Waiter]:
        stmt = select(Waiter).where(Waiter.is_active.is_(True))
        if not include_managers:
            stmt = stmt.where(Waiter.is_manager.is_(False))
        stmt = stmt.order_by(Waiter.name)
        return list(self.session.scalars(stmt))

    def create_waiter(self, name: str, pin: str, *, is_manager: bool = False) -> Waiter:
        name = (name or "").strip()
        pin = (pin or "").strip()
        if not name:
            raise ValidationError("El nombre es obligatorio")
        if not pin or len(pin) < 4:
            raise ValidationError("El PIN debe tener al menos 4 dígitos")
        existing = self.session.scalar(select(Waiter).where(Waiter.pin == pin))
        if existing:
            raise ValidationError("Ya existe un empleado con ese PIN")
        waiter = Waiter(name=name, pin=pin, is_manager=is_manager, is_active=True)
        self.session.add(waiter)
        self.session.flush()
        return waiter

    def update_pin(self, waiter_id: int, new_pin: str) -> Waiter:
        new_pin = (new_pin or "").strip()
        if not new_pin or len(new_pin) < 4:
            raise ValidationError("El PIN debe tener al menos 4 dígitos")
        waiter = self.session.get(Waiter, waiter_id)
        if not waiter or not waiter.is_active:
            raise ValidationError("Empleado no encontrado")
        if waiter.is_manager:
            raise ValidationError("No se puede modificar el PIN del encargado principal")
        existing = self.session.scalar(
            select(Waiter).where(Waiter.pin == new_pin, Waiter.id != waiter_id)
        )
        if existing:
            raise ValidationError("Ese PIN ya está asignado a otro empleado")
        waiter.pin = new_pin
        self.session.flush()
        return waiter

    def delete_waiter(self, waiter_id: int) -> None:
        waiter = self.session.get(Waiter, waiter_id)
        if not waiter or not waiter.is_active:
            raise ValidationError("Empleado no encontrado")
        if waiter.is_manager:
            raise ValidationError("No se puede eliminar a los encargados")
        self.session.delete(waiter)
