"""Reporting utilities."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Tuple

import csv
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Order, Table, Waiter


class ReportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def sales_by_day(self, start: date, end: date) -> List[Tuple[date, int]]:
        stmt = (
            select(func.date(Order.closed_at), func.sum(Order.total_cents))
            .where(
                Order.status == "closed",
                Order.closed_at.is_not(None),
                Order.closed_at >= datetime.combine(start, datetime.min.time()),
                Order.closed_at <= datetime.combine(end, datetime.max.time()),
            )
            .group_by(func.date(Order.closed_at))
            .order_by(func.date(Order.closed_at))
        )
        return [(row[0], row[1] or 0) for row in self.session.execute(stmt)]

    def sales_by_waiter(self, start: date, end: date) -> List[Tuple[str, int]]:
        stmt = (
            select(Waiter.name, func.sum(Order.total_cents))
            .join(Order.waiter)
            .where(
                Order.status == "closed",
                Order.closed_at.is_not(None),
                Order.closed_at >= datetime.combine(start, datetime.min.time()),
                Order.closed_at <= datetime.combine(end, datetime.max.time()),
            )
            .group_by(Waiter.name)
        )
        return [(row[0], row[1] or 0) for row in self.session.execute(stmt)]

    def sales_by_table(self, start: date, end: date) -> List[Tuple[int, int]]:
        stmt = (
            select(Table.number, func.sum(Order.total_cents))
            .join(Order.table)
            .where(
                Order.status == "closed",
                Order.closed_at.is_not(None),
                Order.closed_at >= datetime.combine(start, datetime.min.time()),
                Order.closed_at <= datetime.combine(end, datetime.max.time()),
            )
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
