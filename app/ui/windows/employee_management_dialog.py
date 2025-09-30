"""Dialog for managing waiters and their PINs."""
from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...services import WaiterService


class EmployeeManagementDialog(QDialog):
    """Provides a friendly interface to add or remove waiters."""

    def __init__(self, session_factory, parent=None) -> None:
        super().__init__(parent)
        self.session_factory = session_factory
        self.setModal(True)
        self.setWindowTitle("Gestionar empleados")
        self.setObjectName("employeeDialog")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("dialogCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(24)

        # Employee list
        list_container = QVBoxLayout()
        list_title = QLabel("Empleados activos")
        list_title.setObjectName("sectionTitle")

        self.employee_list = QListWidget()
        self.employee_list.setObjectName("employeeList")
        self.employee_list.currentItemChanged.connect(self._update_actions)

        list_container.addWidget(list_title)
        list_container.addWidget(self.employee_list)

        # Forms
        form_container = QVBoxLayout()
        form_container.setSpacing(20)

        add_title = QLabel("Añadir mesero")
        add_title.setObjectName("sectionSubtitle")

        add_form = QWidget()
        add_form.setObjectName("formCard")
        add_layout = QFormLayout(add_form)
        add_layout.setContentsMargins(24, 24, 24, 24)
        add_layout.setSpacing(16)

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("userInput")
        self.name_edit.setPlaceholderText("Nombre del empleado")

        self.pin_edit = QLineEdit()
        self.pin_edit.setObjectName("pinInput")
        self.pin_edit.setPlaceholderText("PIN de acceso")
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)

        add_layout.addRow("Nombre", self.name_edit)
        add_layout.addRow("PIN", self.pin_edit)

        self.add_button = QPushButton("Agregar empleado")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self._add_employee)

        add_form_layout = QVBoxLayout()
        add_form_layout.setContentsMargins(0, 0, 0, 0)
        add_form_layout.setSpacing(16)
        add_form_layout.addWidget(add_title)
        add_form_layout.addWidget(add_form)
        add_form_layout.addWidget(self.add_button, alignment=Qt.AlignmentFlag.AlignRight)

        form_container.addLayout(add_form_layout)

        update_title = QLabel("Actualizar PIN")
        update_title.setObjectName("sectionSubtitle")

        update_form = QWidget()
        update_form.setObjectName("formCard")
        update_layout = QFormLayout(update_form)
        update_layout.setContentsMargins(24, 24, 24, 24)
        update_layout.setSpacing(16)

        self.new_pin_edit = QLineEdit()
        self.new_pin_edit.setObjectName("pinInput")
        self.new_pin_edit.setPlaceholderText("Nuevo PIN")
        self.new_pin_edit.setEchoMode(QLineEdit.EchoMode.Password)

        update_layout.addRow("Nuevo PIN", self.new_pin_edit)

        self.update_button = QPushButton("Cambiar PIN")
        self.update_button.setObjectName("primaryButton")
        self.update_button.clicked.connect(self._change_pin)

        update_form_layout = QVBoxLayout()
        update_form_layout.setContentsMargins(0, 0, 0, 0)
        update_form_layout.setSpacing(16)
        update_form_layout.addWidget(update_title)
        update_form_layout.addWidget(update_form)
        update_form_layout.addWidget(self.update_button, alignment=Qt.AlignmentFlag.AlignRight)

        form_container.addLayout(update_form_layout)

        self.delete_button = QPushButton("Eliminar mesero")
        self.delete_button.setObjectName("secondaryButton")
        self.delete_button.clicked.connect(self._delete_employee)

        form_container.addWidget(self.delete_button, alignment=Qt.AlignmentFlag.AlignRight)
        form_container.addStretch(1)

        card_layout.addLayout(list_container, 1)
        card_layout.addLayout(form_container, 1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 18)
        shadow.setColor(QColor(30, 136, 229, 70))
        card.setGraphicsEffect(shadow)

        root_layout.addWidget(card)
        self.resize(900, 540)

        self._load_employees()
        self._update_actions()

    def _load_employees(self) -> None:
        session = self.session_factory()
        waiters: List[Waiter]
        try:
            service = WaiterService(session)
            waiters = service.list_waiters(include_managers=True)
        finally:
            session.close()
        self.employee_list.clear()
        for waiter in waiters:
            label = f"{waiter.name} - {'Encargado' if waiter.is_manager else 'Mesero'}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, waiter.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, waiter.is_manager)
            self.employee_list.addItem(item)

    def _selected_waiter(self) -> tuple[int, bool] | None:
        item = self.employee_list.currentItem()
        if not item:
            return None
        waiter_id = item.data(Qt.ItemDataRole.UserRole)
        is_manager = item.data(Qt.ItemDataRole.UserRole + 1)
        if waiter_id is None:
            return None
        return int(waiter_id), bool(is_manager)

    def _add_employee(self) -> None:
        name = self.name_edit.text()
        pin = self.pin_edit.text()
        session = self.session_factory()
        try:
            service = WaiterService(session)
            service.create_waiter(name, pin)
            session.commit()
            QMessageBox.information(self, "Meserito", "Empleado agregado correctamente")
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
            return
        finally:
            session.close()
        self.name_edit.clear()
        self.pin_edit.clear()
        self._load_employees()

    def _change_pin(self) -> None:
        selected = self._selected_waiter()
        if not selected:
            QMessageBox.warning(self, "Meserito", "Seleccione un mesero")
            return
        waiter_id, _ = selected
        new_pin = self.new_pin_edit.text()
        session = self.session_factory()
        try:
            service = WaiterService(session)
            service.update_pin(waiter_id, new_pin)
            session.commit()
            QMessageBox.information(self, "Meserito", "PIN actualizado")
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
            return
        finally:
            session.close()
        self.new_pin_edit.clear()
        self._load_employees()

    def _delete_employee(self) -> None:
        selected = self._selected_waiter()
        if not selected:
            QMessageBox.warning(self, "Meserito", "Seleccione un mesero")
            return
        waiter_id, _ = selected
        answer = QMessageBox.question(
            self,
            "Meserito",
            "¿Seguro que desea eliminar al mesero seleccionado?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        session = self.session_factory()
        try:
            service = WaiterService(session)
            service.delete_waiter(waiter_id)
            session.commit()
            QMessageBox.information(self, "Meserito", "Mesero eliminado")
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Meserito", str(exc))
            return
        finally:
            session.close()
        self._load_employees()

    def _update_actions(self) -> None:
        selected = self._selected_waiter()
        can_edit = bool(selected and not selected[1])
        self.update_button.setEnabled(can_edit)
        self.new_pin_edit.setEnabled(can_edit)
        self.delete_button.setEnabled(can_edit)
