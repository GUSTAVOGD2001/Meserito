"""Entry point for Meserito application."""
from __future__ import annotations

import sys
from pathlib import Path

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
                ("Café americano", 3500, 0, None),
                ("Café latte", 4200, 0, None),
                ("Jugo de naranja", 3800, 0, None),
                ("Chilaquiles", 7500, 1, None),
                ("Hotcakes", 6500, 1, None),
                ("Hamburguesa", 9500, 2, None),
                ("Ensalada", 8200, 2, None),
                ("Pasta Alfredo", 10200, 2, None),
                ("Pastel de chocolate", 5600, 3, None),
                ("Helado", 4200, 3, None),
            ]
            for name, price, cat_index, image_path in menu_items:
                session.add(
                    MenuItem(
                        name=name,
                        price_cents=price,
                        category_id=categories[cat_index].id,
                        image_path=image_path,
                    )
                )
        session.commit()
    finally:
        session.close()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    seed_database()

    app = QApplication(sys.argv)
    stylesheet_path = Path(__file__).resolve().parent / "styles.qss"
    if stylesheet_path.exists():
        app.setStyleSheet(stylesheet_path.read_text(encoding="utf-8"))
    session = SessionLocal()
    auth_service = AuthService(session)
    window = LoginWindow(auth_service, SessionLocal)
    window.show()
    exit_code = app.exec()
    session.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
