"""Entry point for Meserito application."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication
from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import Category, MenuItem, Table, Waiter
from .services import AuthService
from .ui.windows.login_window import LoginWindow


def apply_theme(app: QApplication) -> None:
    """Apply the requested dark theme and consistent control metrics."""
    palette = QPalette()
    background = QColor("#121212")
    surface = QColor("#1f1f1f")
    text = QColor("#ececec")
    accent = QColor("#1e88e5")
    # Paleta oscura para mejorar contraste en toda la app.
    palette.setColor(QPalette.ColorRole.Window, background)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, surface)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#181818"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, surface)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, surface)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(236, 236, 236, 110))
    app.setPalette(palette)

    base_font = QFont("Poppins", 11)
    base_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(base_font)

    base_stylesheet = """
    * {
        color: #ECECEC;
        background-color: transparent;
    }
    QWidget {
        font-size: 15px;
        background-color: #121212;
    }
    QFrame#menuArea,
    QFrame#orderPanel,
    QWidget#dialogCard,
    QWidget#loginCard,
    QWidget#AdminCard,
    QWidget#formCard {
        background-color: #1f1f1f;
        border-radius: 18px;
        border: 1px solid #2c2c2c;
    }
    QPushButton,
    QToolButton {
        min-height: 38px;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 15px;
        background-color: #1e88e5;
        color: #ECECEC;
        border: 1px solid #1e88e5;
    }
    QPushButton:disabled,
    QToolButton:disabled {
        background-color: #2c2c2c;
        border-color: #2c2c2c;
        color: rgba(236, 236, 236, 120);
    }
    QPushButton:hover,
    QToolButton:hover {
        background-color: #42a5f5;
        border-color: #42a5f5;
    }
    QPushButton:pressed,
    QToolButton:pressed {
        background-color: #1565c0;
        border-color: #1565c0;
    }
    QLineEdit,
    QComboBox,
    QSpinBox,
    QTextEdit,
    QPlainTextEdit {
        min-height: 34px;
        padding: 6px 12px;
        border-radius: 8px;
        background-color: #181818;
        border: 1px solid #2c2c2c;
        color: #ECECEC;
        selection-background-color: #1e88e5;
    }
    QTabBar::tab {
        min-height: 38px;
        padding: 8px 16px;
        border-radius: 8px;
        margin: 0 4px;
        background-color: #1f1f1f;
        color: #ECECEC;
    }
    QTabBar::tab:selected {
        background-color: #263238;
        color: #ECECEC;
    }
    QTabWidget::pane {
        border: 1px solid #2c2c2c;
        border-radius: 12px;
        padding: 8px;
    }
    QHeaderView::section {
        background-color: #1f1f1f;
        color: #ECECEC;
        padding: 8px;
        border: none;
        border-bottom: 1px solid #2c2c2c;
    }
    QTableView,
    QTableWidget {
        background-color: #181818;
        gridline-color: #2c2c2c;
        alternate-background-color: #1f1f1f;
    }
    QListWidget,
    QTreeWidget,
    QScrollArea {
        background-color: transparent;
    }
    """

    stylesheet_path = Path(__file__).resolve().parent / "styles.qss"
    styles = []
    if stylesheet_path.exists():
        styles.append(stylesheet_path.read_text(encoding="utf-8"))
    # Añadimos la hoja de estilo oscura al final para asegurar prioridad.
    styles.append(base_stylesheet)
    app.setStyleSheet("\n".join(styles))


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
    apply_theme(app)
    session = SessionLocal()
    auth_service = AuthService(session)
    window = LoginWindow(auth_service, SessionLocal)
    window.show()
    exit_code = app.exec()
    session.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
