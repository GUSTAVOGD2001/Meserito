"""Domain specific exceptions for services."""
from __future__ import annotations


class DomainError(RuntimeError):
    """Base error for domain issues."""


class AuthenticationError(DomainError):
    """Raised when authentication fails."""


class ValidationError(DomainError):
    """Raised when validation fails in the service layer."""
