"""Login window with keypad dialog."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
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
        self.setObjectName("loginWindow")
        self._child_windows: list[QMainWindow] = []

        background = QWidget()
        background.setObjectName("backgroundWidget")
        background_layout = QVBoxLayout(background)
        background_layout.setContentsMargins(48, 48, 48, 48)
        background_layout.setSpacing(0)

        card = QWidget()
        card.setObjectName("loginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(40, 48, 40, 40)

        title = QLabel("Meserito")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Sistema de gestión para restaurantes")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        user_label = QLabel("Código de empleado")
        user_label.setObjectName("promptLabel")

        self.user_edit = QLineEdit()
        self.user_edit.setObjectName("userInput")
        self.user_edit.setPlaceholderText("Ingrese su usuario")

        prompt_label = QLabel("Ingrese su PIN")
        prompt_label.setObjectName("promptLabel")

        self.pin_edit = QLineEdit()
        self.pin_edit.setObjectName("pinInput")
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_edit.setPlaceholderText("****")

        keypad_btn = QPushButton("Abrir teclado")
        keypad_btn.setObjectName("secondaryButton")
        keypad_btn.clicked.connect(self._open_keypad)

        login_btn = QPushButton("Entrar")
        login_btn.setObjectName("primaryButton")
        login_btn.clicked.connect(self._handle_login)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)
        card_layout.addWidget(user_label)
        card_layout.addWidget(self.user_edit)
        card_layout.addWidget(prompt_label)
        card_layout.addWidget(self.pin_edit)
        card_layout.addWidget(keypad_btn)
        card_layout.addWidget(login_btn)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(20)
        shadow.setColor(QColor(30, 136, 229, 80))
        card.setGraphicsEffect(shadow)

        background_layout.addStretch(1)
        background_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        background_layout.addStretch(1)

        self.setCentralWidget(background)
        self.setMinimumSize(640, 480)

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
        self.user_edit.clear()

