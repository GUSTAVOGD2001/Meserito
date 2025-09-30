"""Widget for browsing the menu grouped by category."""
from __future__ import annotations

from typing import Callable, Iterable

from PyQt6.QtWidgets import (
    QGridLayout,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...models import Category, MenuItem


class MenuBrowser(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("menuBrowser")
        self._items_by_category: dict[int, list[MenuItem]] = {}
        self.on_item_selected: Callable[[MenuItem], None] | None = None

        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar...")
        self.search.setObjectName("searchInput")
        self.search.textChanged.connect(self._filter_items)
        layout.addWidget(self.search)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("menuTabs")
        layout.addWidget(self.tabs)

    def set_menu(self, categories: Iterable[Category], items: Iterable[MenuItem]) -> None:
        self.tabs.clear()
        self._items_by_category.clear()
        for category in categories:
            self._items_by_category[category.id] = []
        for item in items:
            self._items_by_category.setdefault(item.category_id, []).append(item)
        for category in categories:
            widget = QWidget()
            grid = QGridLayout(widget)
            grid.setSpacing(16)
            row = col = 0
            for menu_item in self._items_by_category.get(category.id, []):
                button = QPushButton(f"{menu_item.name}\n${menu_item.price_cents/100:.2f}")
                button.setObjectName("menuItemButton")
                button.setMinimumSize(160, 110)
                button.clicked.connect(
                    lambda checked=False, item=menu_item: self._handle_item_clicked(item)
                )
                grid.addWidget(button, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
            self.tabs.addTab(widget, category.name)

    def _handle_item_clicked(self, item: MenuItem) -> None:
        if self.on_item_selected:
            self.on_item_selected(item)

    def _filter_items(self, text: str) -> None:
        text = text.strip().lower()
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            layout = widget.layout()
            if not isinstance(layout, QGridLayout):
                continue
            for i in range(layout.count()):
                button = layout.itemAt(i).widget()
                if not isinstance(button, QPushButton):
                    continue
                button.setVisible(text in button.text().lower())
