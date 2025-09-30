"""Entry point for Meserito application."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication
from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import Category, MenuItem, Table, Waiter
from .services import AuthService
from .ui.windows.login_window import LoginWindow


def seed_database() -> None:
    session = SessionLocal()
    try:
        if session.scalar(select(Waiter).limit(1)) is None:
            waiters = [
                Waiter(name="Ana", pin="1111", is_manager=False),
                Waiter(name="Luis", pin="2222", is_manager=False),
                Waiter(name="Encargado", pin="0000", is_manager=True),
            ]
            session.add_all(waiters)
        if session.scalar(select(Table).limit(1)) is None:
            tables = [
                Table(number=i + 1, x=100 * i, y=100, capacity=4)
                for i in range(4)
            ]
            session.add_all(tables)
        if session.scalar(select(Category).limit(1)) is None:
            categories = [
                Category(name="Bebidas", sort_order=1),
                Category(name="Desayunos", sort_order=2),
                Category(name="Comidas", sort_order=3),
                Category(name="Postres", sort_order=4),
            ]
            session.add_all(categories)
            session.flush()
            menu_items = [
                ("Café americano", 3500, 0),
                ("Café latte", 4200, 0),
                ("Jugo de naranja", 3800, 0),
                ("Chilaquiles", 7500, 1),
                ("Hotcakes", 6500, 1),
                ("Hamburguesa", 9500, 2),
                ("Ensalada", 8200, 2),
                ("Pasta Alfredo", 10200, 2),
                ("Pastel de chocolate", 5600, 3),
                ("Helado", 4200, 3),
            ]
            for name, price, cat_index in menu_items:
                session.add(
                    MenuItem(
                        name=name,
                        price_cents=price,
                        category_id=categories[cat_index].id,
                    )
                )
        session.commit()
    finally:
        session.close()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    seed_database()

    app = QApplication(sys.argv)
    session = SessionLocal()
    auth_service = AuthService(session)
    window = LoginWindow(auth_service, SessionLocal)
    window.show()
    exit_code = app.exec()
    session.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
