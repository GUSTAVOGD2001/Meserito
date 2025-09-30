"""Main window for waiters."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...event_bus import event_bus
from ...models import Table, Waiter
from ...services import MenuService, OrderService, TableService, TicketService
from ..components.cart_sidebar import CartSidebar
from ..components.menu_browser import MenuBrowser
from ..components.table_widget import TableWidget


class MenuDialog(QDialog):
    def __init__(self, menu_service: MenuService, order_service: OrderService, order_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir pedido")
        self.menu_service = menu_service
        self.order_service = order_service
        self.order_id = order_id

        layout = QVBoxLayout(self)
        self.browser = MenuBrowser()
        self.browser.on_item_selected = self._on_item
        layout.addWidget(self.browser)
        self._reload()

    def _reload(self) -> None:
        categories = self.menu_service.list_categories(active_only=True)
        items = []
        for cat in categories:
            items.extend(self.menu_service.list_items(category_id=cat.id))
        self.browser.set_menu(categories, items)

    def _on_item(self, menu_item) -> None:
        self.order_service.add_item(self.order_id, menu_item.id, qty=1)
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
        layout = QHBoxLayout(central)

        self.table_container = QWidget()
        self.table_grid = QGridLayout(self.table_container)
        layout.addWidget(self.table_container, 1)

        right_panel = QVBoxLayout()
        self.info_label = QLabel("Seleccione una mesa")
        right_panel.addWidget(self.info_label)

        self.open_button = QPushButton("Abrir pedido")
        self.open_button.clicked.connect(self._open_order)
        right_panel.addWidget(self.open_button)

        self.add_button = QPushButton("Añadir pedido")
        self.add_button.clicked.connect(self._add_item)
        right_panel.addWidget(self.add_button)

        self.cart = CartSidebar()
        self.cart.checkout_button.clicked.connect(self._close_order)
        right_panel.addWidget(self.cart)

        layout.addLayout(right_panel)

        self.setCentralWidget(central)
        self._load_tables()

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

    def _add_item(self) -> None:
        if not self.selected_table_id:
            QMessageBox.warning(self, "Meserito", "Seleccione una mesa")
            return
        if not self.current_order_id:
            QMessageBox.warning(self, "Meserito", "Primero abra un pedido")
            return
        session = self.session_factory()
        try:
            menu_service = MenuService(session)
            order_service = OrderService(session)
            dialog = MenuDialog(menu_service, order_service, self.current_order_id, self)
            if dialog.exec():
                order_service.compute_totals(self.current_order_id)
                session.commit()
                table_service = TableService(session)
                table_service.mark_occupied(self.selected_table_id)
                session.commit()
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
