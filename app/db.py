"""Database configuration for Meserito."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
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
