"""Numeric keypad dialog for PIN entry."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QGridLayout, QLineEdit, QPushButton, QVBoxLayout


class KeypadDialog(QDialog):
    def __init__(self, title: str = "Ingrese PIN", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(self.input)

        grid = QGridLayout()
        buttons = [str(i) for i in range(1, 10)] + ["borrar", "0", "ok"]
        positions = [(i // 3, i % 3) for i in range(12)]
        for pos, label in zip(positions, buttons, strict=False):
            btn = QPushButton(label.capitalize())
            btn.clicked.connect(lambda checked=False, l=label: self._handle_button(l))
            grid.addWidget(btn, *pos)
        layout.addLayout(grid)

    def _handle_button(self, label: str) -> None:
        if label == "ok":
            self.accept()
        elif label == "borrar":
            current = self.input.text()
            self.input.setText(current[:-1])
        else:
            self.input.setText(self.input.text() + label)

    def get_value(self) -> str:
        return self.input.text()
