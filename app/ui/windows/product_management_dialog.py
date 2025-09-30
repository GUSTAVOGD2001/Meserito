"""Dialog that lets managers curate the restaurant menu."""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...services import MenuService
from ...viewmodels import MenuItemInfo
from ..components.product_card import ProductCard


class ProductManagementDialog(QDialog):
    """Allow managers to add new products with images."""

    def __init__(self, session_factory, parent=None) -> None:
        super().__init__(parent)
        self.session_factory = session_factory
        self.setModal(True)
        self.setWindowTitle("Gestión de productos")
        self.setObjectName("productDialog")
        self.selected_image_path: Optional[str] = None
        self.categories: List[tuple[int, str]] = []
        self.products_by_category: Dict[int, List[MenuItemInfo]] = {}
        self.all_products: List[MenuItemInfo] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("dialogCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(24)

        # Form panel
        form_panel = QWidget()
        form_panel.setObjectName("formCard")
        form_layout = QVBoxLayout(form_panel)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(16)

        form_title = QLabel("Añadir nuevo producto")
        form_title.setObjectName("sectionTitle")

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("userInput")
        self.name_edit.setPlaceholderText("Nombre del producto")

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setObjectName("priceSpin")
        self.price_spin.setRange(0.0, 100000.0)
        self.price_spin.setSuffix(" $")
        self.price_spin.setDecimals(2)
        self.price_spin.setSingleStep(5.0)

        self.category_combo = QComboBox()
        self.category_combo.setObjectName("comboInput")

        self.image_preview = QLabel()
        self.image_preview.setObjectName("imagePreview")
        self.image_preview.setFixedSize(220, 160)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_preview(None)

        image_button = QPushButton("Seleccionar foto")
        image_button.setObjectName("secondaryButton")
        image_button.clicked.connect(self._choose_image)

        add_button = QPushButton("Guardar producto")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._save_product)
        self.add_button = add_button

        form_layout.addWidget(form_title)
        form_layout.addWidget(self.name_edit)
        form_layout.addWidget(self.price_spin)
        form_layout.addWidget(self.category_combo)
        form_layout.addWidget(self.image_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(image_button)
        form_layout.addStretch(1)
        form_layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Gallery panel
        gallery_panel = QWidget()
        gallery_panel.setObjectName("formCard")
        gallery_layout = QVBoxLayout(gallery_panel)
        gallery_layout.setContentsMargins(24, 24, 24, 24)
        gallery_layout.setSpacing(16)

        gallery_title = QLabel("Productos registrados")
        gallery_title.setObjectName("sectionTitle")

        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("comboInput")
        self.filter_combo.currentIndexChanged.connect(self._render_products)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("menuScroll")
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(18)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.grid_widget)

        gallery_layout.addWidget(gallery_title)
        gallery_layout.addWidget(self.filter_combo)
        gallery_layout.addWidget(self.scroll_area, 1)

        card_layout.addWidget(form_panel, 1)
        card_layout.addWidget(gallery_panel, 2)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 18)
        shadow.setColor(QColor(30, 136, 229, 70))
        card.setGraphicsEffect(shadow)

        root_layout.addWidget(card)
        self.resize(1100, 640)

        self._refresh_data()

    def _refresh_data(self) -> None:
        session = self.session_factory()
        try:
            service = MenuService(session)
            categories = service.list_categories(active_only=True)
            self.categories = [(cat.id, cat.name) for cat in categories]
            self.products_by_category = {}
            self.all_products = []
            for cat in categories:
                items = [
                    MenuItemInfo(
                        id=item.id,
                        name=item.name,
                        price_cents=item.price_cents,
                        category_id=item.category_id,
                        image_path=item.image_path,
                    )
                    for item in service.list_items(category_id=cat.id, include_inactive=False)
                ]
                self.products_by_category[cat.id] = items
                self.all_products.extend(items)
        finally:
            session.close()
        self._populate_category_inputs()
        self._render_products()

    def _populate_category_inputs(self) -> None:
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        for cat_id, name in self.categories:
            self.category_combo.addItem(name, cat_id)
        self.category_combo.blockSignals(False)

        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItem("Todos", None)
        for cat_id, name in self.categories:
            self.filter_combo.addItem(name, cat_id)
        self.filter_combo.blockSignals(False)

        if self.categories:
            self.category_combo.setCurrentIndex(0)
        self.filter_combo.setCurrentIndex(0)

        has_categories = bool(self.categories)
        self.category_combo.setEnabled(has_categories)
        self.add_button.setEnabled(has_categories)
        if not has_categories:
            self.category_combo.addItem("Crea una categoría primero", None)

    def _render_products(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        category_id = self.filter_combo.currentData()
        if category_id is None:
            products = self.all_products
        else:
            products = self.products_by_category.get(category_id, [])
        if not products:
            empty = QLabel("No hay productos en esta categoría todavía")
            empty.setObjectName("sectionSubtitle")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(empty, 0, 0)
            return
        for index, info in enumerate(products):
            card = ProductCard(
                title=info.name,
                price_text=f"${info.price_cents / 100:.2f}",
                image_path=info.image_path,
            )
            row = index // 3
            col = index % 3
            self.grid_layout.addWidget(card, row, col)

    def _choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar imagen",
            "",
            "Archivos de imagen (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path:
            return
        self.selected_image_path = path
        self._update_preview(path)

    def _update_preview(self, path: Optional[str]) -> None:
        pixmap = QPixmap()
        if path:
            pixmap = QPixmap(path)
        if pixmap.isNull():
            pixmap = QPixmap(220, 160)
            pixmap.fill(Qt.GlobalColor.lightGray)
        self.image_preview.setPixmap(
            pixmap.scaled(
                self.image_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _save_product(self) -> None:
        name = self.name_edit.text().strip()
        category_id = self.category_combo.currentData()
        if not name or category_id is None:
            QMessageBox.warning(self, "Meserito", "Completa el nombre y selecciona una categoría")
            return
        price_cents = int(round(self.price_spin.value() * 100))
        session = self.session_factory()
        try:
            service = MenuService(session)
            service.create_item(
                category_id=category_id,
                name=name,
                price_cents=price_cents,
                image_path=self.selected_image_path,
            )
            session.commit()
            QMessageBox.information(self, "Meserito", "Producto guardado")
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
            return
        finally:
            session.close()
        self.name_edit.clear()
        self.price_spin.setValue(0.0)
        self.selected_image_path = None
        self._update_preview(None)
        self._refresh_data()
