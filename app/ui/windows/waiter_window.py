"""Modern POS-style main window for waiters."""
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
)

from ...event_bus import event_bus
from ...models import Table, Waiter
from ...services import MenuService, OrderService, TableService, TicketService
from ..components.product_card import ProductCard
from ..viewmodels import MenuItemInfo


class OrderItemRow(QFrame):
    """Row that displays an order item with quantity and remove action."""

    remove_requested = pyqtSignal(int)

    def __init__(
        self,
        item_id: int,
        name: str,
        qty: int,
        total_cents: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.item_id = item_id
        self.setObjectName("orderItemRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        name_label = QLabel(name)
        name_label.setObjectName("orderItemName")
        name_label.setWordWrap(True)

        qty_label = QLabel(f"x{qty}")
        qty_label.setObjectName("orderItemQty")

        total_label = QLabel(f"${total_cents / 100:.2f}")
        total_label.setObjectName("orderItemPrice")

        remove_btn = QPushButton("Eliminar")
        remove_btn.setObjectName("removeItemButton")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(self._emit_remove)

        layout.addWidget(name_label, 1)
        layout.addWidget(qty_label)
        layout.addWidget(total_label)
        layout.addWidget(remove_btn)

    def _emit_remove(self) -> None:
        self.remove_requested.emit(self.item_id)


class QuantityDialog(QDialog):
    """Dialog to request the quantity of a selected product."""

    def __init__(self, menu_item: MenuItemInfo, parent: QWidget | None = None) -> None:
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
    """Main POS window showing sidebar, product grid and order detail."""

    def __init__(self, waiter: Waiter, session_factory, parent=None) -> None:
        super().__init__(parent)
        self.waiter = waiter
        self.session_factory = session_factory
        self.setWindowTitle(f"Meserito - Mesero {waiter.name}")
        self.selected_table_id: Optional[int] = None
        self.current_order_id: Optional[int] = None
        self.tables_by_id: Dict[int, Table] = {}
        self.menu_categories: List[tuple[int, str]] = []
        self.menu_items_by_category: Dict[int, List[MenuItemInfo]] = {}
        self.category_buttons: Dict[int, QPushButton] = {}
        self.active_category_id: Optional[int] = None
        self.order_item_rows: Dict[int, OrderItemRow] = {}

        event_bus.subscribe("table_status_changed", self._handle_table_event)
        event_bus.subscribe("order_updated", self._handle_order_event)

        self._build_ui()
        self.setMinimumSize(1280, 768)
        self._update_status_badge("Sin mesa", "empty")
        self._load_tables()
        self._load_menu()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("posBackground")
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # Sidebar navigation
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(120)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 24, 12, 24)
        sidebar_layout.setSpacing(12)

        style = self.style()
        nav_items = [
            ("Menú", QStyle.StandardPixmap.SP_FileDialogContentsView),
            ("Órdenes", QStyle.StandardPixmap.SP_FileDialogDetailedView),
            ("Historial", QStyle.StandardPixmap.SP_DialogOpenButton),
            ("Reportes", QStyle.StandardPixmap.SP_ComputerIcon),
            ("Configuración", QStyle.StandardPixmap.SP_FileDialogListView),
        ]
        self.sidebar_buttons: List[QPushButton] = []
        for index, (text, icon_enum) in enumerate(nav_items):
            button = QPushButton(text)
            button.setObjectName("sidebarButton")
            button.setFlat(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(style.standardIcon(icon_enum))
            button.setIconSize(QSize(24, 24))
            if index == 0:
                button.setProperty("active", True)
            sidebar_layout.addWidget(button)
            self.sidebar_buttons.append(button)
        sidebar_layout.addStretch(1)

        # Central menu area
        self.menu_area = QFrame()
        self.menu_area.setObjectName("menuArea")
        menu_layout = QVBoxLayout(self.menu_area)
        menu_layout.setContentsMargins(24, 24, 24, 24)
        menu_layout.setSpacing(18)

        title = QLabel("Menú de productos")
        title.setObjectName("posTitle")
        subtitle = QLabel("Explora las categorías y añade productos al pedido.")
        subtitle.setObjectName("posSubtitle")
        subtitle.setWordWrap(True)

        self.category_scroll = QScrollArea()
        self.category_scroll.setObjectName("categoryScroll")
        self.category_scroll.setWidgetResizable(True)
        self.category_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.category_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.categories_widget = QWidget()
        self.categories_layout = QHBoxLayout(self.categories_widget)
        self.categories_layout.setContentsMargins(0, 0, 0, 0)
        self.categories_layout.setSpacing(12)
        self.category_scroll.setWidget(self.categories_widget)

        self.products_scroll = QScrollArea()
        self.products_scroll.setObjectName("productsScroll")
        self.products_scroll.setWidgetResizable(True)
        self.products_widget = QWidget()
        self.products_layout = QGridLayout(self.products_widget)
        self.products_layout.setContentsMargins(0, 0, 0, 0)
        self.products_layout.setHorizontalSpacing(18)
        self.products_layout.setVerticalSpacing(18)
        self.products_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        for column in range(3):
            self.products_layout.setColumnStretch(column, 1)
        self.products_scroll.setWidget(self.products_widget)

        menu_layout.addWidget(title)
        menu_layout.addWidget(subtitle)
        menu_layout.addWidget(self.category_scroll)
        menu_layout.addWidget(self.products_scroll, 1)

        # Order detail panel
        self.order_panel = QFrame()
        self.order_panel.setObjectName("orderPanel")
        self.order_panel.setMinimumWidth(360)
        order_layout = QVBoxLayout(self.order_panel)
        order_layout.setContentsMargins(24, 24, 24, 24)
        order_layout.setSpacing(16)

        header_row = QHBoxLayout()
        self.order_title = QLabel("Orden POS")
        self.order_title.setObjectName("orderTitle")
        self.status_chip = QLabel("Sin mesa")
        self.status_chip.setObjectName("statusChip")
        header_row.addWidget(self.order_title)
        header_row.addStretch(1)
        header_row.addWidget(self.status_chip)

        self.order_subtitle = QLabel("Selecciona una mesa para comenzar")
        self.order_subtitle.setObjectName("orderSubtitle")
        self.order_subtitle.setWordWrap(True)

        selection_row = QHBoxLayout()
        selection_label = QLabel("Mesa")
        selection_label.setObjectName("orderSectionLabel")
        self.table_combo = QComboBox()
        self.table_combo.setObjectName("tableSelector")
        self.table_combo.currentIndexChanged.connect(self._table_combo_changed)
        self.open_order_button = QPushButton("Abrir pedido")
        self.open_order_button.setObjectName("openOrderButton")
        self.open_order_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_order_button.clicked.connect(self._open_order)
        selection_row.addWidget(selection_label)
        selection_row.addWidget(self.table_combo, 1)
        selection_row.addWidget(self.open_order_button)

        self.items_scroll = QScrollArea()
        self.items_scroll.setObjectName("orderScroll")
        self.items_scroll.setWidgetResizable(True)
        self.items_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.items_widget = QWidget()
        self.items_layout = QVBoxLayout(self.items_widget)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(12)
        self.items_scroll.setWidget(self.items_widget)

        self.empty_order_label = QLabel("No hay productos en la orden actual")
        self.empty_order_label.setObjectName("emptyOrderLabel")
        self.empty_order_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        totals_box = QFrame()
        totals_box.setObjectName("totalsBox")
        totals_layout = QVBoxLayout(totals_box)
        totals_layout.setContentsMargins(16, 16, 16, 16)
        totals_layout.setSpacing(8)
        self.subtotal_label = QLabel("Subtotal: $0.00")
        self.subtotal_label.setObjectName("subtotalLabel")
        self.discount_label = QLabel("Descuento: $0.00")
        self.discount_label.setObjectName("discountLabel")
        self.tax_label = QLabel("Impuestos: $0.00")
        self.tax_label.setObjectName("taxLabel")
        self.total_label = QLabel("Total: $0.00")
        self.total_label.setObjectName("totalAmountLabel")
        totals_layout.addWidget(self.subtotal_label)
        totals_layout.addWidget(self.discount_label)
        totals_layout.addWidget(self.tax_label)
        totals_layout.addWidget(self.total_label)

        self.print_button = QPushButton("Imprimir")
        self.print_button.setObjectName("printButton")
        self.print_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.print_button.setMinimumHeight(48)
        self.print_button.clicked.connect(self._print_order)

        self.finalize_button = QPushButton("Finalizar orden")
        self.finalize_button.setObjectName("finalizeButton")
        self.finalize_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.finalize_button.setMinimumHeight(54)
        self.finalize_button.clicked.connect(self._close_order)

        order_layout.addLayout(header_row)
        order_layout.addWidget(self.order_subtitle)
        order_layout.addLayout(selection_row)
        order_layout.addWidget(self.items_scroll, 1)
        order_layout.addWidget(totals_box)
        order_layout.addWidget(self.print_button)
        order_layout.addWidget(self.finalize_button)

        main_layout.addWidget(self.sidebar, 0)
        main_layout.addWidget(self.menu_area, 1)
        main_layout.addWidget(self.order_panel, 0)

        self.setCentralWidget(central)
        self._clear_order_detail()

    def _load_tables(self, preserve_selection: bool = False) -> None:
        session = self.session_factory()
        try:
            service = TableService(session)
            tables = service.list_tables()
        finally:
            session.close()

        previous_selection = self.selected_table_id if preserve_selection else None
        self.tables_by_id = {table.id: table for table in tables}

        self.table_combo.blockSignals(True)
        self.table_combo.clear()
        for table in tables:
            display_name = table.name or f"Mesa {table.number}"
            status_text = self._format_status(table.status)
            subtitle = f"Mesa {table.number}"
            if table.name:
                display_name = f"{table.name} · {subtitle}"
            self.table_combo.addItem(f"{display_name} ({status_text})", table.id)
        self.table_combo.blockSignals(False)

        if not tables:
            self.selected_table_id = None
            self._refresh_order()
            return

        target_id = previous_selection if previous_selection in self.tables_by_id else tables[0].id
        index = self.table_combo.findData(target_id)
        if index == -1:
            index = 0
            target_id = self.table_combo.itemData(index)
        self.table_combo.blockSignals(True)
        self.table_combo.setCurrentIndex(index)
        self.table_combo.blockSignals(False)
        self.selected_table_id = int(target_id) if target_id is not None else None
        self._refresh_order()

    def _table_combo_changed(self, index: int) -> None:
        if index < 0:
            self.selected_table_id = None
            self._refresh_order()
            return
        table_id = self.table_combo.itemData(index)
        self.selected_table_id = int(table_id) if table_id is not None else None
        self._refresh_order()

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
        self._load_tables(preserve_selection=True)

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
        self._load_tables(preserve_selection=True)

    def _print_order(self) -> None:
        if not self.current_order_id:
            QMessageBox.warning(self, "Meserito", "No hay pedido abierto para imprimir")
            return
        session = self.session_factory()
        try:
            order_service = OrderService(session)
            order = order_service.compute_totals(self.current_order_id)
            ticket_service = TicketService(session)
            output = Path("tickets") / f"ticket_{order.id}.pdf"
            ticket_service.generate_pdf(order.id, output)
            session.commit()
            QMessageBox.information(
                self,
                "Meserito",
                f"Ticket generado en {output}"
            )
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()

    def _handle_table_event(self, payload: dict) -> None:
        table_id = payload.get("table_id")
        status = payload.get("status")
        if table_id in self.tables_by_id and status:
            self.tables_by_id[table_id].status = status
        self._load_tables(preserve_selection=True)

    def _handle_order_event(self, payload: dict) -> None:
        if payload.get("order_id") == self.current_order_id:
            self._refresh_order()

    def _load_menu(self) -> None:
        session = self.session_factory()
        try:
            menu_service = MenuService(session)
            categories = menu_service.list_categories(active_only=True)
            self.menu_categories = [(cat.id, cat.name) for cat in categories]
            self.menu_items_by_category = {
                cat.id: [
                    MenuItemInfo(
                        id=item.id,
                        name=item.name,
                        price_cents=item.price_cents,
                        category_id=item.category_id,
                        image_path=item.image_path,
                    )
                    for item in menu_service.list_items(category_id=cat.id)
                ]
                for cat in categories
            }
        finally:
            session.close()
        self._render_categories()
        self._render_products()

    def _render_categories(self) -> None:
        self.category_buttons.clear()
        self.active_category_id = self.active_category_id or (
            self.menu_categories[0][0] if self.menu_categories else None
        )

        while self.categories_layout.count():
            item = self.categories_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.menu_categories:
            placeholder = QLabel("Sin categorías")
            placeholder.setObjectName("emptyCategoriesLabel")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.categories_layout.addWidget(placeholder)
            self.categories_layout.addStretch(1)
            self.active_category_id = None
            return

        for category_id, name in self.menu_categories:
            button = QPushButton(name)
            button.setObjectName("categoryButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, cid=category_id: self._set_active_category(cid)
            )
            self.categories_layout.addWidget(button)
            self.category_buttons[category_id] = button
        self.categories_layout.addStretch(1)

        if self.active_category_id in self.category_buttons:
            self.category_buttons[self.active_category_id].setChecked(True)
        else:
            first_id = self.menu_categories[0][0]
            self.active_category_id = first_id
            self.category_buttons[first_id].setChecked(True)

    def _set_active_category(self, category_id: int) -> None:
        if self.active_category_id == category_id:
            return
        if self.active_category_id in self.category_buttons:
            self.category_buttons[self.active_category_id].setChecked(False)
        self.active_category_id = category_id
        if category_id in self.category_buttons:
            self.category_buttons[category_id].setChecked(True)
        self._render_products()

    def _render_products(self) -> None:
        while self.products_layout.count():
            item = self.products_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        products: List[MenuItemInfo] = []
        if self.active_category_id is not None:
            products = self.menu_items_by_category.get(self.active_category_id, [])

        if not products:
            placeholder = QLabel("No hay productos en esta categoría")
            placeholder.setObjectName("emptyProductsLabel")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.products_layout.addWidget(placeholder, 0, 0, 1, 3)
            return

        for index, info in enumerate(products):
            card = ProductCard(
                title=info.name,
                price_text=f"${info.price_cents / 100:.2f}",
                image_path=info.image_path,
            )
            handler = partial(self._prompt_quantity, info)
            card.clicked.connect(handler)
            card.add_requested.connect(handler)
            row = index // 3
            col = index % 3
            self.products_layout.addWidget(card, row, col)

    def _prompt_quantity(self, menu_item: MenuItemInfo) -> None:
        if not self.selected_table_id or not self.current_order_id:
            QMessageBox.warning(self, "Meserito", "Seleccione una mesa y abra un pedido primero")
            return
        dialog = QuantityDialog(menu_item, self)
        if not dialog.exec():
            return
        self._add_item_to_order(menu_item.id, dialog.quantity)

    def _add_item_to_order(self, menu_item_id: int, quantity: int) -> None:
        if not self.current_order_id or not self.selected_table_id:
            return
        session = self.session_factory()
        try:
            order_service = OrderService(session)
            table_service = TableService(session)
            order_service.add_item(self.current_order_id, menu_item_id, qty=quantity)
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

    def _remove_order_item(self, item_id: int) -> None:
        if not self.current_order_id:
            return
        session = self.session_factory()
        try:
            service = OrderService(session)
            service.void_item(item_id, "Eliminado desde POS")
            service.compute_totals(self.current_order_id)
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
            return
        finally:
            session.close()
        self._refresh_order()

    def _refresh_order(self) -> None:
        if not self.selected_table_id:
            self.current_order_id = None
            self.order_title.setText("Orden POS")
            self.order_subtitle.setText("Selecciona una mesa para comenzar")
            self._update_status_badge("Sin mesa", "empty")
            self.open_order_button.setEnabled(False)
            self.print_button.setEnabled(False)
            self.finalize_button.setEnabled(False)
            self._update_totals(0, 0, 0, 0)
            self._clear_order_detail()
            return

        session = self.session_factory()
        try:
            table_service = TableService(session)
            table = table_service.get_table(self.selected_table_id)
            self.tables_by_id[table.id] = table
            display_name = table.name or f"Mesa {table.number}"
            status_text = self._format_status(table.status)
            self.order_title.setText(display_name)
            self.order_subtitle.setText(f"Mesa {table.number} · {status_text}")
            self._update_status_badge(status_text, table.status)
            self.current_order_id = table.current_order_id

            if self.current_order_id:
                order_service = OrderService(session)
                order = order_service.get_order(self.current_order_id)
                items = [
                    {
                        "id": item.id,
                        "name": item.menu_item.name,
                        "qty": item.qty,
                        "total_cents": item.qty * item.unit_price_cents,
                    }
                    for item in order.items
                    if item.status != "void"
                ]
                self._populate_order_items(items)
                discount_cents = max(
                    0,
                    (order.subtotal_cents + order.tax_cents) - order.total_cents,
                )
                self._update_totals(
                    order.subtotal_cents,
                    discount_cents,
                    order.tax_cents,
                    order.total_cents,
                )
                self.print_button.setEnabled(True)
                self.finalize_button.setEnabled(True)
            else:
                self._clear_order_detail()
                self._update_totals(0, 0, 0, 0)
                self.print_button.setEnabled(False)
                self.finalize_button.setEnabled(False)

            self.open_order_button.setEnabled(self.current_order_id is None)
        finally:
            session.close()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        event_bus.unsubscribe("table_status_changed", self._handle_table_event)
        event_bus.unsubscribe("order_updated", self._handle_order_event)
        super().closeEvent(event)

    def _populate_order_items(self, items: List[Dict[str, int | str]]) -> None:
        self.order_item_rows.clear()
        self._clear_items_layout()
        if not items:
            self._show_empty_order_message()
            return

        for item in items:
            widget = OrderItemRow(
                int(item["id"]),
                str(item["name"]),
                int(item["qty"]),
                int(item["total_cents"]),
            )
            widget.remove_requested.connect(self._remove_order_item)
            self.items_layout.addWidget(widget)
            self.order_item_rows[int(item["id"])] = widget
        self.items_layout.addStretch(1)

    def _clear_order_detail(self) -> None:
        self.order_item_rows.clear()
        self._clear_items_layout()
        self._show_empty_order_message()

    def _clear_items_layout(self) -> None:
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                if widget is self.empty_order_label:
                    widget.setParent(None)
                else:
                    widget.deleteLater()

    def _show_empty_order_message(self) -> None:
        if self.empty_order_label.parent() is not None:
            self.empty_order_label.setParent(None)
        self.items_layout.addWidget(self.empty_order_label)
        self.items_layout.addStretch(1)

    def _update_totals(self, subtotal: int, discount: int, tax: int, total: int) -> None:
        self.subtotal_label.setText(f"Subtotal: ${subtotal / 100:.2f}")
        self.discount_label.setText(f"Descuento: ${discount / 100:.2f}")
        self.tax_label.setText(f"Impuestos: ${tax / 100:.2f}")
        self.total_label.setText(f"Total: ${total / 100:.2f}")

    def _update_status_badge(self, text: str, status: str) -> None:
        self.status_chip.setText(text)
        self.status_chip.setProperty("status", status)
        self.status_chip.style().unpolish(self.status_chip)
        self.status_chip.style().polish(self.status_chip)

    def _format_status(self, status: Optional[str]) -> str:
        return {
            "free": "Libre",
            "active": "Activo",
            "occupied": "Ocupado",
            "closed": "Cerrado",
            None: "Sin estado",
        }.get(status, status or "Sin estado")
