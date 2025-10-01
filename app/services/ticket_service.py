"""Ticket generation service."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Order, Ticket
from .exceptions import DomainError


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
            "table": order.table.number,
            "waiter": order.waiter.name,
            "covers": order.covers,
            "opened_at": order.opened_at.isoformat(),
            "closed_at": order.closed_at.isoformat() if order.closed_at else None,
            "items": items,
            "subtotal_cents": order.subtotal_cents,
            "tax_cents": order.tax_cents,
            "total_cents": order.total_cents,
        }

    def generate_pdf(self, order_id: int, output_path: Path, ticket_type: str = "cliente") -> Path:
        payload = self.build_ticket_payload(order_id)
        self._render_pdf(payload, output_path)
        self._persist_ticket(order_id, ticket_type, output_path)
        return output_path

    def _persist_ticket(self, order_id: int, ticket_type: str, output_path: Path) -> Ticket:
        ticket = self.session.scalar(
            select(Ticket).where(Ticket.order_id == order_id, Ticket.type == ticket_type)
        )
        if ticket:
            ticket.file_path = str(output_path)
            ticket.created_at = datetime.utcnow()
        else:
            ticket = Ticket(
                order_id=order_id,
                type=ticket_type,
                file_path=str(output_path),
            )
            self.session.add(ticket)
        self.session.flush()
        return ticket

    def _render_pdf(self, payload: Dict, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter
        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"Ticket pedido #{payload['order_id']}")
        y -= 20
        c.setFont("Helvetica", 11)
        c.drawString(50, y, f"Mesa: {payload['table']}")
        y -= 15
        c.drawString(50, y, f"Mesero: {payload['waiter']}")
        y -= 15
        c.drawString(50, y, f"Personas: {payload['covers']}")
        y -= 20
        c.drawString(50, y, "Items:")
        y -= 20
        for item in payload["items"]:
            c.drawString(60, y, f"{item['qty']} x {item['name']}")
            c.drawRightString(width - 60, y, f"${item['total_cents']/100:.2f}")
            y -= 15
        y -= 10
        c.drawRightString(width - 60, y, f"Subtotal: ${payload['subtotal_cents']/100:.2f}")
        y -= 15
        c.drawRightString(width - 60, y, f"Impuestos: ${payload['tax_cents']/100:.2f}")
        y -= 15
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - 60, y, f"Total: ${payload['total_cents']/100:.2f}")
        y -= 30
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Emitido: {datetime.now():%Y-%m-%d %H:%M}")
        c.showPage()
        c.save()
