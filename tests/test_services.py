from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import Category, MenuItem, Table, Waiter
from app.services.order_service import OrderService
from app.services.table_service import TableService


class ServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, future=True)

    def test_compute_totals(self) -> None:
        session: Session = self.Session()
        try:
            waiter = Waiter(name="Tester", pin="9999")
            table = Table(number=1)
            category = Category(name="Test")
            item = MenuItem(name="Platillo", price_cents=1000, category=category)
            session.add_all([waiter, table, category, item])
            session.commit()

            order_service = OrderService(session)
            order = order_service.get_or_create_open_order(table.id, waiter.id, covers=2)
            order_service.add_item(order.id, item.id, qty=3)
            order_service.compute_totals(order.id)

            self.assertEqual(order.subtotal_cents, 3000)
            self.assertEqual(order.tax_cents, int(round(3000 * 0.16)))
            self.assertEqual(order.total_cents, order.subtotal_cents + order.tax_cents)
        finally:
            session.close()

    def test_open_and_close_order_updates_table(self) -> None:
        session: Session = self.Session()
        try:
            waiter = Waiter(name="Tester", pin="8888")
            table = Table(number=5)
            session.add_all([waiter, table])
            session.commit()

            service = TableService(session)
            order = service.open_order(table.id, waiter.id, covers=2)
            self.assertEqual(table.current_order_id, order.id)
            self.assertEqual(table.status, "active")

            service.close_order(table.id)
            self.assertIsNone(table.current_order_id)
            self.assertEqual(table.status, "free")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
