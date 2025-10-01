"""Ticket generation service."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Order, Ticket
from ..printing.ticket import print_ticket_document
from .exceptions import DomainError


def _resolve_datetime(payload: Dict) -> datetime:
    """Return a datetime object from the payload, falling back to utcnow."""

    closed_dt = payload.get("closed_at_dt")
    if isinstance(closed_dt, datetime):
        return closed_dt
    closed_at = payload.get("closed_at")
    if isinstance(closed_at, str):
        try:
            return datetime.fromisoformat(closed_at)
        except ValueError:  # pragma: no cover - defensive
            pass
    return datetime.utcnow()


class TicketService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_ticket_payload(self, order_id: int) -> Dict:
        order = self.session.get(Order, order_id)
        if not order:
            raise DomainError("Pedido no encontrado")
        items = [
            {
                "name": item.menu_item.name,
                "qty": item.qty,
                "unit_price_cents": item.unit_price_cents,
                "total_cents": item.qty * item.unit_price_cents,
                "status": item.status,
            }
            for item in order.items
            if item.status != "void"
        ]
        return {
            "order_id": order.id,
            "table": order.table.number if order.table else None,
            "waiter": order.waiter.name if order.waiter else None,
            "covers": order.covers,
            "opened_at": order.opened_at.isoformat(),
            "closed_at": order.closed_at.isoformat() if order.closed_at else None,
            "closed_at_dt": order.closed_at,
            "items": items,
            "subtotal_cents": order.subtotal_cents,
            "tax_cents": order.tax_cents,
            "total_cents": order.total_cents,
            "discount_cents": getattr(order, "discount_cents", 0),
            "payment_type": order.payment_type,
            "card_last4": order.card_last4,
        }

    def generate_pdf(self, order_id: int, output_path: Path, ticket_type: str = "cliente") -> Path:
        payload = self.build_ticket_payload(order_id)
        created_at = _resolve_datetime(payload)
        enriched_payload = {
            **payload,
            "restaurant_name": "Meserito",
            "receipt_title": "RECIBO DE COBRO",
            "mesa": payload.get("table"),
            "mesero": payload.get("waiter"),
            "created_at": created_at,
        }
        printed_path = print_ticket_document(enriched_payload, output_path)
        final_path = printed_path or output_path
        self._persist_ticket(order_id, ticket_type, final_path, payload)
        return final_path

    def _persist_ticket(
        self,
        order_id: int,
        ticket_type: str,
        output_path: Path,
        payload: Dict,
    ) -> Ticket:
        ticket = self.session.scalar(
            select(Ticket).where(Ticket.order_id == order_id, Ticket.type == ticket_type)
        )
        if ticket:
            ticket.file_path = str(output_path)
            ticket.created_at = datetime.utcnow()
            ticket.payment_type = payload.get("payment_type")
            ticket.card_last4 = payload.get("card_last4")
        else:
            ticket = Ticket(
                order_id=order_id,
                type=ticket_type,
                file_path=str(output_path),
                payment_type=payload.get("payment_type"),
                card_last4=payload.get("card_last4"),
            )
            self.session.add(ticket)
        self.session.flush()
        # TODO: Registrar intentos fallidos de impresión.
        return ticket
