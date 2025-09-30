"""Authentication service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Waiter
from .exceptions import AuthenticationError


class AuthService:
    """Service responsible for authentication operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def login(self, pin: str) -> Waiter:
        waiter = (
            self.session.query(Waiter)
            .filter(Waiter.pin == pin, Waiter.is_active.is_(True))
            .one_or_none()
        )
        if not waiter:
            raise AuthenticationError("PIN inválido")
        return waiter
