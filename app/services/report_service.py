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
    OrdersByDay,
    OrdersByTable,
    OrdersByWaiter,
    Table,
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
