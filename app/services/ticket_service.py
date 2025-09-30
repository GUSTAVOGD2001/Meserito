"""Ticket generation service."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
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

    def generate_pdf(self, order_id: int, output_path: Path) -> Path:
        payload = self.build_ticket_payload(order_id)
        ticket = self._ensure_ticket(order_id, payload)
        self._render_pdf(ticket, payload, output_path)
        return output_path

    def _ensure_ticket(self, order_id: int, payload: Dict) -> Ticket:
        ticket = self.session.scalar(select(Ticket).where(Ticket.order_id == order_id))
        if ticket:
            ticket.payload_json = json.dumps(payload, ensure_ascii=False)
            ticket.total_cents = payload["total_cents"]
            self.session.flush()
            return ticket
        last_number = self.session.scalar(select(func.max(Ticket.number))) or 0
        ticket = Ticket(
            order_id=order_id,
            number=last_number + 1,
            payload_json=json.dumps(payload, ensure_ascii=False),
            total_cents=payload["total_cents"],
        )
        self.session.add(ticket)
        self.session.flush()
        return ticket

    def _render_pdf(self, ticket: Ticket, payload: Dict, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter
        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"Ticket #{ticket.number}")
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
