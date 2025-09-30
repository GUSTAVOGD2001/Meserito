"""Sidebar displaying current order items."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget


class CartSidebar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setObjectName("cartSidebar")
        self.order_id: int | None = None
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("cartList")
        self.totals_label = QLabel("Total: $0.00")
        self.totals_label.setObjectName("totalsLabel")
        self.checkout_button = QPushButton("Cerrar cuenta")
        self.checkout_button.setObjectName("primaryButton")

        layout = QVBoxLayout(self)
        self.header = QLabel("Cuenta actual")
        self.header.setObjectName("sidebarHeader")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.totals_label)
        layout.addWidget(self.checkout_button)

    def set_items(self, items: list[dict], subtotal: int, tax: int, total: int) -> None:
        self.list_widget.clear()
        for entry in items:
            text = f"{entry['qty']} x {entry['name']} - ${entry['total_cents']/100:.2f}"
            QListWidgetItem(text, self.list_widget)
        self.totals_label.setText(
            f"Subtotal: ${subtotal/100:.2f}\nImpuestos: ${tax/100:.2f}\nTotal: ${total/100:.2f}"
        )
