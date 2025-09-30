"""Manager window providing administrative tools."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDateEdit,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import Category, MenuItem, Table, Waiter
from ...services import MenuService, ReportService, TableService
from .floorplan_editor import FloorplanEditor
from .employee_management_dialog import EmployeeManagementDialog
from .product_management_dialog import ProductManagementDialog


class ManagerWindow(QMainWindow):
    def __init__(self, manager: Waiter, session_factory, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.session_factory = session_factory
        self.setWindowTitle(f"Meserito - Encargado {manager.name}")

        self.setMinimumSize(1200, 720)

        central = QWidget()
        central.setObjectName("backgroundWidget")
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(48, 48, 48, 48)
        main_layout.setSpacing(32)

        title = QLabel("Meserito")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel("Panel de gestión para encargados")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)

        actions_card = QWidget()
        actions_card.setObjectName("contentCard")
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(32, 32, 32, 32)
        actions_layout.setSpacing(24)

        self.employee_button = QPushButton("Gestionar empleados")
        self.employee_button.setObjectName("heroButton")
        self.employee_button.setMinimumHeight(72)
        self.employee_button.clicked.connect(self._open_employee_dialog)

        self.product_button = QPushButton("Gestionar productos")
        self.product_button.setObjectName("heroButton")
        self.product_button.setMinimumHeight(72)
        self.product_button.clicked.connect(self._open_product_dialog)

        actions_layout.addWidget(self.employee_button)
        actions_layout.addWidget(self.product_button)
        actions_layout.addStretch(1)

        tabs_card = QWidget()
        tabs_card.setObjectName("contentCard")
        tabs_layout = QVBoxLayout(tabs_card)
        tabs_layout.setContentsMargins(24, 24, 24, 24)
        tabs_layout.setSpacing(16)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("managerTabs")
        tabs_layout.addWidget(self.tabs)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(actions_card)
        main_layout.addWidget(tabs_card, 1)

        self.setCentralWidget(central)
        self._apply_shadow(actions_card)
        self._apply_shadow(tabs_card)

        # Floorplan tab
        floorplan_tab = QWidget()
        fp_layout = QVBoxLayout(floorplan_tab)
        self.floorplan = FloorplanEditor()
        self.floorplan.table_moved.connect(self._update_table_position)
        fp_layout.addWidget(self.floorplan)
        add_table_btn = QPushButton("Agregar mesa")
        add_table_btn.setObjectName("primaryButton")
        add_table_btn.clicked.connect(self._add_table)
        fp_layout.addWidget(add_table_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.tabs.addTab(floorplan_tab, "Plano")

        # Menu tab
        menu_tab = QWidget()
        menu_layout = QHBoxLayout(menu_tab)
        menu_layout.setSpacing(24)

        left_panel = QWidget()
        left_panel.setObjectName("formCard")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(24, 24, 24, 24)
        left_layout.setSpacing(16)

        categories_title = QLabel("Categorías")
        categories_title.setObjectName("sectionTitle")

        self.category_list = QListWidget()
        self.category_list.setObjectName("managerList")
        self.category_list.currentItemChanged.connect(lambda *_: self._load_items())

        add_cat = QPushButton("Agregar categoría")
        add_cat.setObjectName("primaryButton")
        add_cat.clicked.connect(self._add_category)

        toggle_cat = QPushButton("Activar/Desactivar")
        toggle_cat.setObjectName("secondaryButton")
        toggle_cat.clicked.connect(self._toggle_category)

        left_layout.addWidget(categories_title)
        left_layout.addWidget(self.category_list, 1)
        left_layout.addWidget(add_cat)
        left_layout.addWidget(toggle_cat)

        right_panel = QWidget()
        right_panel.setObjectName("formCard")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setSpacing(16)

        items_title = QLabel("Productos")
        items_title.setObjectName("sectionTitle")

        self.item_list = QListWidget()
        self.item_list.setObjectName("managerList")

        add_item = QPushButton("Agregar platillo")
        add_item.setObjectName("primaryButton")
        add_item.clicked.connect(self._add_item)

        toggle_item = QPushButton("Activar/Desactivar platillo")
        toggle_item.setObjectName("secondaryButton")
        toggle_item.clicked.connect(self._toggle_item)

        right_layout.addWidget(items_title)
        right_layout.addWidget(self.item_list, 1)
        right_layout.addWidget(add_item)
        right_layout.addWidget(toggle_item)

        menu_layout.addWidget(left_panel, 1)
        menu_layout.addWidget(right_panel, 1)
        self.tabs.addTab(menu_tab, "Menú")

        # Reports tab
        reports_tab = QWidget()
        rep_layout = QVBoxLayout(reports_tab)
        rep_layout.setSpacing(20)

        reports_title = QLabel("Reportes de ventas")
        reports_title.setObjectName("sectionTitle")

        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(date.today())
        self.end_date = QDateEdit()
        self.end_date.setDate(date.today())
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(self.end_date)
        refresh = QPushButton("Generar")
        refresh.setObjectName("primaryButton")
        refresh.clicked.connect(self._refresh_reports)
        date_layout.addWidget(refresh)

        self.report_table = QTableWidget(0, 3)
        self.report_table.setHorizontalHeaderLabels(["Fecha/Mesero/Mesa", "Total", "Tipo"])

        export_btn = QPushButton("Exportar CSV")
        export_btn.setObjectName("secondaryButton")
        export_btn.clicked.connect(self._export_reports)

        rep_layout.addWidget(reports_title)
        rep_layout.addLayout(date_layout)
        rep_layout.addWidget(self.report_table, 1)
        rep_layout.addWidget(export_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.tabs.addTab(reports_tab, "Reportes")

        self._load_tables()
        self._load_categories()
        self._refresh_reports()

    def _load_tables(self) -> None:
        session = self.session_factory()
        try:
            service = TableService(session)
            tables = service.list_tables()
        finally:
            session.close()
        self.floorplan.load_tables(tables)

    def _open_employee_dialog(self) -> None:
        dialog = EmployeeManagementDialog(self.session_factory, self)
        dialog.exec()

    def _open_product_dialog(self) -> None:
        dialog = ProductManagementDialog(self.session_factory, self)
        dialog.exec()
        self._load_categories()
        self._load_items()

    def _apply_shadow(self, widget: QWidget) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 20)
        shadow.setColor(QColor(30, 136, 229, 70))
        widget.setGraphicsEffect(shadow)

    def _add_table(self) -> None:
        session = self.session_factory()
        try:
            service = TableService(session)
            number = len(service.list_tables()) + 1
            service.create_table(number=number)
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()
        self._load_tables()

    def _update_table_position(self, table_id: int, x: int, y: int) -> None:
        session = self.session_factory()
        try:
            service = TableService(session)
            service.update_table(table_id, x=x, y=y)
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()

    # Menu management
    def _load_categories(self) -> None:
        session = self.session_factory()
        try:
            service = MenuService(session)
            categories = service.list_categories(active_only=False)
        finally:
            session.close()
        self.category_list.clear()
        for category in categories:
            item = QListWidgetItem(f"{category.name} ({'Activo' if category.is_active else 'Inactivo'})")
            item.setData(Qt.ItemDataRole.UserRole, category.id)
            self.category_list.addItem(item)
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def _load_items(self) -> None:
        current = self.category_list.currentItem()
        self.item_list.clear()
        if not current:
            return
        category_id = current.data(Qt.ItemDataRole.UserRole)
        session = self.session_factory()
        try:
            service = MenuService(session)
            items = service.list_items(category_id=category_id, include_inactive=True)
        finally:
            session.close()
        for entry in items:
            item = QListWidgetItem(
                f"{entry.name} ${entry.price_cents/100:.2f} ({'Activo' if entry.is_active else 'Inactivo'})"
            )
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self.item_list.addItem(item)

    def _add_category(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "Nueva categoría", "Nombre")
        if not ok or not name:
            return
        session = self.session_factory()
        try:
            service = MenuService(session)
            service.create_category(name=name)
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()
        self._load_categories()
        self._load_items()

    def _toggle_category(self) -> None:
        current = self.category_list.currentItem()
        if not current:
            return
        category_id = current.data(Qt.ItemDataRole.UserRole)
        session = self.session_factory()
        try:
            category = session.get(Category, category_id)
            if not category:
                raise ValueError("Categoría no encontrada")
            category.is_active = not category.is_active
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()
        self._load_categories()

    def _add_item(self) -> None:
        current = self.category_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Meserito", "Seleccione una categoría")
            return
        category_id = current.data(Qt.ItemDataRole.UserRole)
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "Nuevo platillo", "Nombre")
        if not ok or not name:
            return
        price, ok = QInputDialog.getInt(self, "Precio", "Precio en centavos", 1000, 0)
        if not ok:
            return
        session = self.session_factory()
        try:
            service = MenuService(session)
            service.create_item(category_id=category_id, name=name, price_cents=price)
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()
        self._load_items()

    def _toggle_item(self) -> None:
        current = self.item_list.currentItem()
        if not current:
            return
        item_id = current.data(Qt.ItemDataRole.UserRole)
        session = self.session_factory()
        try:
            item = session.get(MenuItem, item_id)
            if not item:
                raise ValueError("Platillo no encontrado")
            item.is_active = not item.is_active
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()
        self._load_items()

    # Reports
    def _refresh_reports(self) -> None:
        session = self.session_factory()
        try:
            service = ReportService(session)
            start = self.start_date.date().toPyDate()
            end = self.end_date.date().toPyDate()
            day_rows = service.sales_by_day(start, end)
            waiter_rows = service.sales_by_waiter(start, end)
            table_rows = service.sales_by_table(start, end)
        finally:
            session.close()
        data = []
        data.extend([(str(d), total, "Día") for d, total in day_rows])
        data.extend([(name, total, "Mesero") for name, total in waiter_rows])
        data.extend([(str(number), total, "Mesa") for number, total in table_rows])
        self.report_table.setRowCount(len(data))
        for row_idx, (label, total, kind) in enumerate(data):
            self.report_table.setItem(row_idx, 0, QTableWidgetItem(label))
            self.report_table.setItem(row_idx, 1, QTableWidgetItem(f"${total/100:.2f}"))
            self.report_table.setItem(row_idx, 2, QTableWidgetItem(kind))

    def _export_reports(self) -> None:
        session = self.session_factory()
        try:
            service = ReportService(session)
            start = self.start_date.date().toPyDate()
            end = self.end_date.date().toPyDate()
            rows = service.sales_by_day(start, end)
            path = Path("reportes") / "ventas_dia.csv"
            service.export_to_csv(rows, ["Fecha", "Total"], path)
            QMessageBox.information(self, "Meserito", f"Reporte exportado a {path}")
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
        finally:
            session.close()
