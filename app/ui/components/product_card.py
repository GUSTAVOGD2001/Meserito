"""Reusable product cards with image and price."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class ProductCard(QFrame):
    """Stylized card that displays product information."""

    clicked = pyqtSignal()

    def __init__(
        self,
        *,
        title: str,
        price_text: str,
        image_path: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("productCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._selected = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.image_label = QLabel()
        self.image_label.setObjectName("productImage")
        self.image_label.setFixedSize(160, 120)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("productName")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.price_label = QLabel(price_text)
        self.price_label.setObjectName("productPrice")
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.price_label)

        layout.addStretch(1)
        self.setMinimumSize(180, 220)
        self._apply_image(image_path)

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self.setProperty("selected", value)
        self.style().unpolish(self)
        self.style().polish(self)

    def is_selected(self) -> bool:
        return self._selected

    def update_content(self, *, title: Optional[str] = None, price_text: Optional[str] = None) -> None:
        if title is not None:
            self.title_label.setText(title)
        if price_text is not None:
            self.price_label.setText(price_text)

    def set_image(self, image_path: Optional[str]) -> None:
        self._apply_image(image_path)

    def _apply_image(self, image_path: Optional[str]) -> None:
        pixmap = QPixmap()
        if image_path:
            candidate = Path(image_path)
            if candidate.exists():
                pixmap = QPixmap(str(candidate))
        if pixmap.isNull():
            pixmap = QPixmap(160, 120)
            pixmap.fill(Qt.GlobalColor.lightGray)
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
