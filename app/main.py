"""Entry point for Meserito application."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QApplication, QHeaderView, QTableView, QTableWidget
from sqlalchemy import select

from .db import Base, SessionLocal, engine, run_migrations
from .models import Category, MenuItem, Table, Waiter
from .services import AuthService
from .ui.windows.login_window import LoginWindow


class _HeaderAutoResizer(QObject):
    """Ensure table headers resize contents for better readability."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # pragma: no cover - GUI hook
        if event.type() == QEvent.Type.Show and isinstance(watched, (QTableView, QTableWidget)):
            header = watched.horizontalHeader()
            if header is not None:
                header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
                header.setStretchLastSection(True)
        return super().eventFilter(watched, event)


def apply_theme(app: QApplication) -> None:
    """Apply high-contrast Meserito dark theme and control metrics."""

    base_font = QFont("Poppins", 11)
    base_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    base_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(base_font)

    stylesheet_path = Path(__file__).resolve().parent / "styles.qss"
    styles: list[str] = []
    if stylesheet_path.exists():
        styles.append(stylesheet_path.read_text(encoding="utf-8"))

    base_stylesheet = """
    * { color: #E9EEF5; }
    QMainWindow, QWidget { background: #0F1216; }
    QGroupBox, QFrame, QTabWidget::pane { background: #161A20; border: 1px solid #1C222B; border-radius: 12px; }
    QPushButton { background: #1E66FF; border: none; border-radius: 12px; min-height: 40px; padding: 10px 16px; font-weight: 600; }
    QPushButton:hover { background: #2A70FF; }
    QPushButton:pressed { background: #1556D0; }
    QPushButton:disabled { background: #2A3550; color: #9BA7B4; }
    QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox { background: #0F1216; border: 1px solid #273140; border-radius: 10px; min-height: 36px; padding: 6px 10px; }
    QHeaderView::section { background: #1C222B; color: #E9EEF5; padding: 6px; border: none; }
    QTabBar::tab { background: #161A20; padding: 8px 14px; margin-right: 6px; border-radius: 10px; }
    QTabBar::tab:selected { background: #1C222B; }
    QLabel[heading="true"] { font-size: 22px; font-weight: 800; color: #E9EEF5; }
    .QSuccess { background: #1DB954; }
    .QWarn { background: #FF9800; }
    .QDanger { background: #EF4444; }
    QListView, QTreeView, QTableView, QTableWidget { background: #0F1216; alternate-background-color: #161A20; gridline-color: #1C222B; }
    QScrollBar:vertical { background: #161A20; width: 12px; margin: 2px; }
    QScrollBar::handle:vertical { background: #273140; border-radius: 6px; }
    """
    styles.append(base_stylesheet)
    app.setStyleSheet("\n".join(styles))

    resizer = _HeaderAutoResizer(app)
    app.installEventFilter(resizer)
    app._meserito_header_resizer = resizer  # type: ignore[attr-defined]
    # TODO: Persist custom table sizing preferences per view.


def _enable_high_dpi() -> None:
    """
    Activa HiDPI de forma compatible:
    - En Qt6: solo ajusta la política de redondeo (HiDPI ya viene activo).
    - En Qt5: activa AA_UseHighDpiPixmaps y AA_EnableHighDpiScaling si existen.
    Debe llamarse ANTES de crear QApplication.
    """

    # HiDPI fix (Qt6/Qt5-safe)
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass

    for attr_name in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
        try:
            attr = getattr(Qt.ApplicationAttribute, attr_name)
        except AttributeError:
            continue
        QCoreApplication.setAttribute(attr, True)


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
    run_migrations()
    seed_database()

    _enable_high_dpi()

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
