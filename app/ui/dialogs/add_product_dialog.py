"""Dialog to browse the menu in a touch-friendly way."""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...models import Category
from ...services import MenuService
from ...viewmodels import MenuItemInfo
from ..components.product_card import ProductCard


class AddProductDialog(QDialog):
    """Touch friendly dialog to add products to an order."""

    def __init__(self, session_factory, parent=None) -> None:
        super().__init__(parent)
        self.session_factory = session_factory
        self.setModal(True)
        self.setWindowTitle("Añadir producto")
        self.setObjectName("addProductDialog")
        self._items_by_category: Dict[int, List[MenuItemInfo]] = {}
        self._selected_item: Optional[MenuItemInfo] = None
        self._card_map: Dict[int, ProductCard] = {}

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("dialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(20)

        title = QLabel("Selecciona un producto")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Navega por las categorías y elige el platillo para agregarlo al pedido")
        subtitle.setObjectName("sectionSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        self.category_combo = QComboBox()
        self.category_combo.setObjectName("comboInput")
        self.category_combo.currentIndexChanged.connect(self._render_products)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("menuScroll")
        self.products_widget = QWidget()
        self.products_layout = QGridLayout(self.products_widget)
        self.products_layout.setSpacing(18)
        self.products_layout.setContentsMargins(12, 12, 12, 12)
        self.scroll_area.setWidget(self.products_widget)

        quantity_label = QLabel("Cantidad")
        quantity_label.setObjectName("promptLabel")
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setObjectName("quantitySpin")
        self.quantity_spin.setRange(1, 20)
        self.quantity_spin.setValue(1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(16)

        back_btn = QPushButton("Atrás")
        back_btn.setObjectName("secondaryButton")
        back_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Confirmar")
        confirm_btn.setObjectName("primaryButton")
        confirm_btn.clicked.connect(self._confirm_selection)

        buttons_layout.addWidget(back_btn)
        buttons_layout.addWidget(confirm_btn)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.category_combo)
        card_layout.addWidget(self.scroll_area, stretch=1)
        card_layout.addWidget(quantity_label)
        card_layout.addWidget(self.quantity_spin)
        card_layout.addLayout(buttons_layout)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 18)
        shadow.setColor(QColor(30, 136, 229, 70))
        card.setGraphicsEffect(shadow)

        root_layout.addWidget(card)

        self.resize(720, 640)
        self._load_menu()

    def selected_item(self) -> Optional[MenuItemInfo]:
        return self._selected_item

    def quantity(self) -> int:
        return self.quantity_spin.value()

    # Internal helpers
    def _load_menu(self) -> None:
        session = self.session_factory()
        categories: List[Category]
        try:
            service = MenuService(session)
            categories = service.list_categories(active_only=True)
            self._items_by_category = {
                category.id: [
                    MenuItemInfo(
                        id=item.id,
                        name=item.name,
                        price_cents=item.price_cents,
                        category_id=item.category_id,
                        image_path=item.image_path,
                    )
                    for item in service.list_items(category_id=category.id)
                ]
                for category in categories
            }
        finally:
            session.close()
        self._populate_categories(categories)

    def _populate_categories(self, categories: List[Category]) -> None:
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        for category in categories:
            self.category_combo.addItem(category.name, category.id)
        self.category_combo.blockSignals(False)
        if categories:
            self._render_products(0)

    def _render_products(self, index: int) -> None:
        self._card_map.clear()
        while self.products_layout.count():
            item = self.products_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        category_id = self.category_combo.currentData()
        if category_id is None:
            return
        products = self._items_by_category.get(category_id, [])
        row = col = 0
        for info in products:
            card = ProductCard(
                title=info.name,
                price_text=f"${info.price_cents / 100:.2f}",
                image_path=info.image_path,
            )
            card.clicked.connect(lambda checked=False, data=info: self._select_item(data))
            self.products_layout.addWidget(card, row, col)
            self._card_map[info.id] = card
            col += 1
            if col >= 3:
                col = 0
                row += 1
        self.products_layout.setRowStretch(row + 1, 1)
        self._selected_item = None
        self.quantity_spin.setValue(1)

    def _select_item(self, info: MenuItemInfo) -> None:
        self._selected_item = info
        for card in self._card_map.values():
            card.set_selected(False)
        card = self._card_map.get(info.id)
        if card:
            card.set_selected(True)

    def _confirm_selection(self) -> None:
        if not self._selected_item:
            QMessageBox.warning(self, "Meserito", "Selecciona un producto antes de continuar")
            return
        if self.quantity_spin.value() <= 0:
            QMessageBox.warning(self, "Meserito", "La cantidad debe ser mayor a cero")
            return
        self.accept()
