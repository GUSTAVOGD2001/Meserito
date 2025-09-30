"""Table widget representing table status."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QPushButton

STATUS_COLORS = {
    "free": QColor("#4CAF50"),
    "active": QColor("#FFC107"),
    "occupied": QColor("#F44336"),
    "closed": QColor("#9E9E9E"),
}


class TableWidget(QPushButton):
    clicked_table = pyqtSignal(int)

    def __init__(self, table_id: int, number: int, parent=None) -> None:
        super().__init__(str(number), parent)
        self.table_id = table_id
        self.status = "free"
        self.setMinimumSize(80, 80)
        self.clicked.connect(lambda: self.clicked_table.emit(self.table_id))
        self.refresh()

    def set_status(self, status: str) -> None:
        self.status = status
        self.refresh()

    def refresh(self) -> None:
        color = STATUS_COLORS.get(self.status, QColor("#607D8B"))
        self.setStyleSheet(
            f"background-color: {color.name()}; color: white; border-radius: 8px; font-size: 16px;"
        )
