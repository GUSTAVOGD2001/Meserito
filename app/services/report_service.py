"""Reporting utilities.

Example usage of the aggregated models::

    session.execute(
        select(OrdersByDay.date, OrdersByDay.total_cents)
        .where(OrdersByDay.date.between(start, end))
        .order_by(OrdersByDay.date)
    )

    session.execute(
        select(Waiter.name, func.sum(OrdersByWaiter.total_cents))
        .join(OrdersByWaiter, OrdersByWaiter.waiter_id == Waiter.id)
        .where(OrdersByWaiter.date.between(start, end))
        .group_by(Waiter.name)
    )

    session.execute(
        select(Table.number, func.sum(OrdersByTable.total_cents))
        .join(OrdersByTable, OrdersByTable.table_id == Table.id)
        .where(OrdersByTable.date.between(start, end))
        .group_by(Table.number)
    )
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable, List, Tuple

import csv
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    Order,
    OrdersByDay,
    OrdersByTable,
    OrdersByWaiter,
    Payment,
    Table,
    Ticket,
    Waiter,
)


class ReportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def sales_by_day(self, start: date, end: date) -> List[Tuple[date, int]]:
        stmt = (
            select(OrdersByDay.date, OrdersByDay.total_cents)
            .where(OrdersByDay.date >= start, OrdersByDay.date <= end)
            .order_by(OrdersByDay.date)
        )
        return [(row[0], row[1] or 0) for row in self.session.execute(stmt)]

    def sales_by_waiter(self, start: date, end: date) -> List[Tuple[str, int]]:
        stmt = (
            select(Waiter.name, func.sum(OrdersByWaiter.total_cents))
            .join(OrdersByWaiter, OrdersByWaiter.waiter_id == Waiter.id)
            .where(OrdersByWaiter.date >= start, OrdersByWaiter.date <= end)
            .group_by(Waiter.name)
        )
        return [(row[0], row[1] or 0) for row in self.session.execute(stmt)]

    def sales_by_table(self, start: date, end: date) -> List[Tuple[int, int]]:
        stmt = (
            select(Table.number, func.sum(OrdersByTable.total_cents))
            .join(OrdersByTable, OrdersByTable.table_id == Table.id)
            .where(OrdersByTable.date >= start, OrdersByTable.date <= end)
            .group_by(Table.number)
        )
        return [(row[0], row[1] or 0) for row in self.session.execute(stmt)]

    def export_to_csv(self, rows: Iterable[Tuple], headers: List[str], path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
        return path

    def closed_orders_report(self, start: date, end: date) -> List[dict]:
        payment_method_sq = (
            select(Payment.method)
            .where(Payment.order_id == Order.id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        ticket_path_sq = (
            select(Ticket.file_path)
            .where(Ticket.order_id == Order.id, Ticket.type == "cliente")
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        stmt = (
            select(
                Order.closed_at,
                Table.name,
                Table.number,
                Waiter.name,
                Order.total_cents,
                payment_method_sq,
                ticket_path_sq,
            )
            .join(Table, Order.table_id == Table.id)
            .join(Waiter, Order.waiter_id == Waiter.id)
            .where(
                Order.status == "closed",
                Order.closed_at.is_not(None),
                func.date(Order.closed_at) >= start,
                func.date(Order.closed_at) <= end,
            )
            .order_by(Order.closed_at.desc())
        )
        rows = []
        for (
            closed_at,
            table_name,
            table_number,
            waiter_name,
            total_cents,
            payment_method,
            ticket_path,
        ) in self.session.execute(stmt):
            fecha = closed_at.strftime("%Y-%m-%d %H:%M") if closed_at else ""
            if table_name:
                mesa = table_name
            elif table_number is not None:
                mesa = f"Mesa {table_number}"
            else:
                mesa = ""
            rows.append(
                {
                    "fecha": fecha,
                    "mesa": mesa,
                    "mesero": waiter_name or "",
                    "total_cents": total_cents or 0,
                    "metodo": payment_method or "",
                    "ticket": ticket_path or "",
                }
            )
        return rows

    def export_closed_orders_csv(self, rows: Iterable[dict], path: Path) -> Path:
        headers = ["Fecha", "Mesa", "Mesero", "Total", "Tipo", "Ticket"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(
                    [
                        row.get("fecha", ""),
                        row.get("mesa", ""),
                        row.get("mesero", ""),
                        f"{(row.get('total_cents', 0) or 0) / 100:.2f}",
                        row.get("metodo", ""),
                        row.get("ticket", ""),
                    ]
                )
        return path
