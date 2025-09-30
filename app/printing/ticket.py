"""Convenience helpers for ticket printing."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from ..services.ticket_service import TicketService


def print_ticket(session: Session, order_id: int, output_path: Path) -> Path:
    """Generate a ticket PDF for the given order using the shared ticket service."""
    service = TicketService(session)
    return service.generate_pdf(order_id, output_path)
