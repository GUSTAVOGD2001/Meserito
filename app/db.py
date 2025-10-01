"""Database configuration for Meserito."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DB_PATH = Path("meserito.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"


def _create_engine(echo: bool = False):
    return create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=echo,
        future=True,
        connect_args={"check_same_thread": False},
    )


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base class for declarative models."""


@contextmanager
def session_scope() -> Generator:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations() -> None:
    """Apply lightweight migrations required for new ticket fields."""

    with engine.begin() as connection:
        ticket_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info('tickets')"))
        }
        if "payment_type" not in ticket_columns:
            connection.execute(text("ALTER TABLE tickets ADD COLUMN payment_type TEXT"))
        if "card_last4" not in ticket_columns:
            connection.execute(text("ALTER TABLE tickets ADD COLUMN card_last4 TEXT"))

        order_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info('orders')"))
        }
        if "payment_type" not in order_columns:
            connection.execute(text("ALTER TABLE orders ADD COLUMN payment_type TEXT"))
        if "card_last4" not in order_columns:
            connection.execute(text("ALTER TABLE orders ADD COLUMN card_last4 TEXT"))
