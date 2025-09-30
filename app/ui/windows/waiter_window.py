"""Main window for waiters with a modern blue/white theme."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
)

from ...event_bus import event_bus
from ...models import MenuItem, Table, Waiter
from ...services import MenuService, OrderService, TableService, TicketService
from ..components.cart_sidebar import CartSidebar
from ..components.menu_browser import MenuBrowser
from ..components.table_widget import TableWidget


class QuantityDialog(QDialog):
    """Dialog to request the quantity of a selected product."""

    def __init__(self, menu_item: MenuItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.menu_item = menu_item
        self.quantity = 1
        self.setWindowTitle("Seleccionar cantidad")
        self.setObjectName("quantityDialog")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("dialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        title = QLabel(menu_item.name)
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        price = QLabel(f"Precio: ${menu_item.price_cents / 100:.2f}")
        price.setObjectName("sectionSubtitle")
        price.setAlignment(Qt.AlignmentFlag.AlignCenter)

        prompt = QLabel("¿Cuántas unidades desea agregar?")
        prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spin_box = QSpinBox()
        self.spin_box.setObjectName("quantitySpin")
        self.spin_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_box.setRange(1, 99)
        self.spin_box.setValue(1)

        buttons = QHBoxLayout()
        back_btn = QPushButton("Atrás")
        back_btn.setObjectName("secondaryButton")
        back_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Confirmar")
        confirm_btn.setObjectName("primaryButton")
        confirm_btn.clicked.connect(self._confirm)

        buttons.addWidget(back_btn)
        buttons.addWidget(confirm_btn)

        card_layout.addWidget(title)
        card_layout.addWidget(price)
        card_layout.addSpacing(10)
        card_layout.addWidget(prompt)
        card_layout.addWidget(self.spin_box)
        card_layout.addLayout(buttons)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 18)
        shadow.setColor(QColor(30, 136, 229, 80))
        card.setGraphicsEffect(shadow)

        layout.addWidget(card)

    def _confirm(self) -> None:
        self.quantity = self.spin_box.value()
        self.accept()


class WaiterWindow(QMainWindow):
    def __init__(self, waiter: Waiter, session_factory, parent=None) -> None:
        super().__init__(parent)
        self.waiter = waiter
        self.session_factory = session_factory
        self.setWindowTitle(f"Meserito - Mesero {waiter.name}")
        self.selected_table_id: Optional[int] = None
        self.current_order_id: Optional[int] = None
        self.table_widgets: dict[int, TableWidget] = {}

        event_bus.subscribe("table_status_changed", self._handle_table_event)
        event_bus.subscribe("order_updated", self._handle_order_event)

        central = QWidget()
        central.setObjectName("backgroundWidget")
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(48, 48, 48, 48)
        main_layout.setSpacing(32)

        title = QLabel("Meserito")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Panel de gestión para empleados")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(24)

        tables_card = QWidget()
        tables_card.setObjectName("contentCard")
        tables_layout = QVBoxLayout(tables_card)
        tables_layout.setContentsMargins(32, 32, 32, 32)
        tables_layout.setSpacing(20)

        tables_title = QLabel("Mesas")
        tables_title.setObjectName("sectionTitle")

        self.info_label = QLabel("Seleccione una mesa para comenzar")
        self.info_label.setObjectName("sectionSubtitle")

        self.table_container = QWidget()
        self.table_grid = QGridLayout(self.table_container)
        self.table_grid.setSpacing(16)

        self.open_button = QPushButton("Abrir pedido")
        self.open_button.setObjectName("primaryButton")
        self.open_button.clicked.connect(self._open_order)

        tables_layout.addWidget(tables_title)
        tables_layout.addWidget(self.info_label)
        tables_layout.addWidget(self.table_container)
        tables_layout.addStretch(1)
        tables_layout.addWidget(self.open_button)

        menu_card = QWidget()
        menu_card.setObjectName("contentCard")
        menu_layout = QVBoxLayout(menu_card)
        menu_layout.setContentsMargins(32, 32, 32, 32)
        menu_layout.setSpacing(20)

        menu_title = QLabel("Menú del restaurante")
        menu_title.setObjectName("sectionTitle")

        menu_hint = QLabel("Selecciona un producto para agregarlo al pedido")
        menu_hint.setObjectName("sectionSubtitle")

        self.menu_browser = MenuBrowser()
        self.menu_browser.on_item_selected = self._handle_menu_item

        menu_layout.addWidget(menu_title)
        menu_layout.addWidget(menu_hint)
        menu_layout.addWidget(self.menu_browser)

        cart_card = QWidget()
        cart_card.setObjectName("contentCard")
        cart_layout = QVBoxLayout(cart_card)
        cart_layout.setContentsMargins(32, 32, 32, 32)
        cart_layout.setSpacing(20)

        cart_title = QLabel("Resumen del pedido")
        cart_title.setObjectName("sectionTitle")

        self.cart = CartSidebar()
        self.cart.checkout_button.clicked.connect(self._close_order)
        if hasattr(self.cart, "header"):
            self.cart.header.hide()

        cart_layout.addWidget(cart_title)
        cart_layout.addWidget(self.cart)
        cart_layout.addStretch(1)

        cards_layout.addWidget(tables_card, 1)
        cards_layout.addWidget(menu_card, 2)
        cards_layout.addWidget(cart_card, 1)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addLayout(cards_layout)

        self._apply_shadow(tables_card)
        self._apply_shadow(menu_card)
        self._apply_shadow(cart_card)

        self.setCentralWidget(central)
        self.setMinimumSize(1200, 720)
        self._load_tables()
        self._load_menu()

    # Session helpers
    def _load_tables(self) -> None:
        session = self.session_factory()
        try:
            service = TableService(session)
            tables = service.list_tables()
        finally:
            session.close()
        self._render_tables(tables)

    def _render_tables(self, tables: list[Table]) -> None:
        for i in reversed(range(self.table_grid.count())):
            widget = self.table_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.table_widgets.clear()
        row = col = 0
        for table in tables:
            widget = TableWidget(table.id, table.number)
            widget.set_status(table.status)
            widget.clicked_table.connect(self._table_selected)
            self.table_grid.addWidget(widget, row, col)
            self.table_widgets[table.id] = widget
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _table_selected(self, table_id: int) -> None:
        self.selected_table_id = table_id
        session = self.session_factory()
        try:
            table = TableService(session).get_table(table_id)
            self.info_label.setText(f"Mesa seleccionada: {table.number}")
        finally:
            session.close()
        self._refresh_order()

    def _refresh_order(self) -> None:
        if not self.selected_table_id:
            return
        session = self.session_factory()
        try:
            table_service = TableService(session)
            table = table_service.get_table(self.selected_table_id)
            self.current_order_id = table.current_order_id
            widget = self.table_widgets.get(table.id)
            if widget:
                widget.set_status(table.status)
            if self.current_order_id:
                order_service = OrderService(session)
                order = order_service.get_order(self.current_order_id)
                items = [
                    {
                        "name": item.menu_item.name,
                        "qty": item.qty,
                        "total_cents": item.qty * item.unit_price_cents,
                    }
                    for item in order.items
                    if item.status != "void"
                ]
                self.cart.order_id = order.id
                self.cart.set_items(items, order.subtotal_cents, order.tax_cents, order.total_cents)
            else:
                self.cart.order_id = None
                self.cart.set_items([], 0, 0, 0)
        finally:
            session.close()

    def _open_order(self) -> None:
        if not self.selected_table_id:
            QMessageBox.warning(self, "Meserito", "Seleccione una mesa")
            return
        covers, ok = QInputDialog.getInt(self, "Abrir pedido", "Número de personas", 2, 1, 12)
        if not ok:
            return
        session = self.session_factory()
        try:
            table_service = TableService(session)
            order = table_service.open_order(self.selected_table_id, self.waiter.id, covers)
            session.commit()
            self.current_order_id = order.id
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()
        self._refresh_order()

    def _close_order(self) -> None:
        if not self.current_order_id or not self.selected_table_id:
            QMessageBox.warning(self, "Meserito", "No hay pedido abierto")
            return
        session = self.session_factory()
        try:
            order_service = OrderService(session)
            table_service = TableService(session)
            order = order_service.compute_totals(self.current_order_id)
            closed_order = table_service.close_order(self.selected_table_id)
            ticket_service = TicketService(session)
            output = Path("tickets") / f"ticket_{order.id}.pdf"
            ticket_service.generate_pdf(closed_order.id, output)
            session.commit()
            QMessageBox.information(
                self,
                "Meserito",
                f"Cuenta cerrada. Ticket guardado en {output}"
            )
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()
        self._refresh_order()

    def _handle_table_event(self, payload: dict) -> None:
        table_id = payload.get("table_id")
        status = payload.get("status")
        widget = self.table_widgets.get(table_id)
        if widget:
            widget.set_status(status)

    def _handle_order_event(self, payload: dict) -> None:
        if payload.get("order_id") == self.current_order_id:
            self._refresh_order()

    def _load_menu(self) -> None:
        session = self.session_factory()
        try:
            menu_service = MenuService(session)
            categories = menu_service.list_categories(active_only=True)
            items = []
            for cat in categories:
                items.extend(menu_service.list_items(category_id=cat.id))
        finally:
            session.close()
        self.menu_browser.set_menu(categories, items)

    def _handle_menu_item(self, menu_item: MenuItem) -> None:
        if not self.selected_table_id or not self.current_order_id:
            QMessageBox.warning(self, "Meserito", "Seleccione una mesa y abra un pedido primero")
            return
        dialog = QuantityDialog(menu_item, self)
        if not dialog.exec():
            return
        session = self.session_factory()
        try:
            order_service = OrderService(session)
            table_service = TableService(session)
            order_service.add_item(self.current_order_id, menu_item.id, qty=dialog.quantity)
            order_service.compute_totals(self.current_order_id)
            table_service.mark_occupied(self.selected_table_id)
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
            return
        finally:
            session.close()
        self._refresh_order()

    def _apply_shadow(self, widget: QWidget) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 20)
        shadow.setColor(QColor(30, 136, 229, 70))
        widget.setGraphicsEffect(shadow)
