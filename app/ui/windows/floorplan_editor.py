"""Floorplan editor for arranging tables."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView, QVBoxLayout, QWidget

from ...models import Table


class TableItem(QGraphicsEllipseItem):
    def __init__(self, table: Table, callback, radius: float = 40.0):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.table = table
        self.callback = callback
        self.setBrush(QBrush(QColor("#4CAF50")))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        label = QGraphicsTextItem(str(table.number), self)
        label.setDefaultTextColor(QColor("white"))
        label.setPos(-10, -10)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        super().mouseReleaseEvent(event)
        pos = self.pos()
        self.callback(self.table.id, int(pos.x()), int(pos.y()))


class FloorplanEditor(QWidget):
    table_moved = pyqtSignal(int, int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view)

    def load_tables(self, tables: list[Table]) -> None:
        self.scene.clear()
        for table in tables:
            item = TableItem(table, self._emit_move)
            item.setPos(QPointF(table.x, table.y))
            self.scene.addItem(item)

    def _emit_move(self, table_id: int, x: int, y: int) -> None:
        self.table_moved.emit(table_id, x, y)
