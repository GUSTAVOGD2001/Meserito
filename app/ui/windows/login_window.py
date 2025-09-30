"""Login window with keypad dialog."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...services import AuthService, AuthenticationError
from ..components.keypad_dialog import KeypadDialog
from .manager_window import ManagerWindow
from .waiter_window import WaiterWindow


class LoginWindow(QMainWindow):
    def __init__(self, auth_service: AuthService, session_factory, parent=None) -> None:
        super().__init__(parent)
        self.auth_service = auth_service
        self.session_factory = session_factory
        self.setWindowTitle("Meserito - Iniciar sesión")
        self._child_windows: list[QMainWindow] = []

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("Ingrese su PIN"))

        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pin_edit)

        keypad_btn = QPushButton("Abrir teclado")
        keypad_btn.clicked.connect(self._open_keypad)
        layout.addWidget(keypad_btn)

        login_btn = QPushButton("Entrar")
        login_btn.clicked.connect(self._handle_login)
        layout.addWidget(login_btn)

        self.setCentralWidget(central)

    def _open_keypad(self) -> None:
        dialog = KeypadDialog(parent=self)
        if dialog.exec():
            self.pin_edit.setText(dialog.get_value())

    def _handle_login(self) -> None:
        pin = self.pin_edit.text().strip()
        if not pin:
            QMessageBox.warning(self, "Meserito", "Ingrese un PIN")
            return
        try:
            waiter = self.auth_service.login(pin)
        except AuthenticationError as exc:
            QMessageBox.critical(self, "Meserito", str(exc))
            return
        window: QMainWindow
        if waiter.is_manager:
            window = ManagerWindow(waiter, self.session_factory)
        else:
            window = WaiterWindow(waiter, self.session_factory)
        window.show()
        self._child_windows.append(window)
        self.pin_edit.clear()
