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

        subtitle = QLabel("Bienvenido, ingrese su PIN para continuar")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        prompt_label = QLabel("Ingrese su PIN")
        prompt_label.setObjectName("promptLabel")

        self.pin_edit = QLineEdit()
        self.pin_edit.setObjectName("pinInput")
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)

        keypad_btn = QPushButton("Abrir teclado")
        keypad_btn.setObjectName("secondaryButton")
        keypad_btn.clicked.connect(self._open_keypad)

        login_btn = QPushButton("Entrar")
        login_btn.setObjectName("primaryButton")
        login_btn.clicked.connect(self._handle_login)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)
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

        self._apply_styles()

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

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            #backgroundWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #e3f2fd,
                    stop: 1 #bbdefb
                );
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }

            #loginCard {
                background-color: #ffffff;
                border-radius: 24px;
            }

            #titleLabel {
                color: #0d47a1;
                font-size: 36px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }

            #subtitleLabel {
                color: #1976d2;
                font-size: 16px;
            }

            #promptLabel {
                color: #0d47a1;
                font-size: 15px;
                font-weight: 600;
            }

            QLineEdit#pinInput {
                padding: 14px 16px;
                border-radius: 12px;
                border: 2px solid #cfe2f3;
                background: #f8fbff;
                color: #0d47a1;
                font-size: 18px;
            }

            QLineEdit#pinInput:focus {
                border: 2px solid #1e88e5;
                background: #ffffff;
            }

            QPushButton#primaryButton,
            QPushButton#secondaryButton {
                padding: 14px 18px;
                border-radius: 14px;
                font-size: 16px;
                font-weight: 600;
                border: 2px solid transparent;
                background-color: #1e88e5;
                color: #ffffff;
            }

            QPushButton#secondaryButton {
                background-color: #1565c0;
            }

            QPushButton#primaryButton:hover,
            QPushButton#secondaryButton:hover {
                background-color: #ffffff;
                color: #1e88e5;
                border: 2px solid #1e88e5;
            }

            QPushButton#primaryButton:pressed,
            QPushButton#secondaryButton:pressed {
                background-color: #e3f2fd;
                color: #0d47a1;
            }
            """
        )
