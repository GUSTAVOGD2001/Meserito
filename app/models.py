"""SQLAlchemy models for Meserito."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Waiter(Base):
    __tablename__ = "waiters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pin: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_manager: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    orders: Mapped[List["Order"]] = relationship(back_populates="waiter")
    daily_sales: Mapped[List["OrdersByWaiter"]] = relationship(
        back_populates="waiter", cascade="all, delete-orphan"
    )


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(50))
    x: Mapped[int] = mapped_column(Integer, default=0)
    y: Mapped[int] = mapped_column(Integer, default=0)
    capacity: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(
        Enum("free", "active", "occupied", "closed", name="table_status"),
        default="free",
        nullable=False,
    )
    current_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"))

    current_order: Mapped[Optional["Order"]] = relationship(
        "Order", foreign_keys=[current_order_id], post_update=True
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="table", foreign_keys="Order.table_id"
    )
    daily_sales: Mapped[List["OrdersByTable"]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    menu_items: Mapped[List["MenuItem"]] = relationship(back_populates="category")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(300))

    category: Mapped[Category] = relationship(back_populates="menu_items")
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="menu_item")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False)
    waiter_id: Mapped[int] = mapped_column(ForeignKey("waiters.id"), nullable=False)
    covers: Mapped[int] = mapped_column(Integer, default=1)
    opened_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column()
    status: Mapped[str] = mapped_column(
        Enum("open", "closed", "cancelled", name="order_status"),
        default="open",
        nullable=False,
    )
    subtotal_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer, default=0)
    total_cents: Mapped[int] = mapped_column(Integer, default=0)
    payment_type: Mapped[Optional[str]] = mapped_column(String(50))
    card_last4: Mapped[Optional[str]] = mapped_column(String(4))

    table: Mapped[Table] = relationship(back_populates="orders", foreign_keys=[table_id])
    waiter: Mapped[Waiter] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("covers >= 1", name="ck_orders_covers_positive"),
        CheckConstraint("subtotal_cents >= 0", name="ck_orders_subtotal_positive"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum("added", "preparing", "served", "void", name="order_item_status"),
        default="added",
        nullable=False,
    )

    order: Mapped[Order] = relationship(back_populates="items")
    menu_item: Mapped[MenuItem] = relationship(back_populates="order_items")

    __table_args__ = (
        CheckConstraint("qty >= 0", name="ck_order_items_qty_non_negative"),
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="cliente", nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    payment_type: Mapped[Optional[str]] = mapped_column(String(50))
    card_last4: Mapped[Optional[str]] = mapped_column(String(4))

    order: Mapped[Order] = relationship(back_populates="tickets")

    __table_args__ = (
        UniqueConstraint("order_id", "type", name="uq_tickets_order_type"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    order: Mapped[Order] = relationship(back_populates="payments")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_type: Mapped[str] = mapped_column(
        Enum("waiter", "manager", "system", name="audit_actor_type"), nullable=False
    )
    actor_id: Mapped[Optional[int]] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    payload_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)


class OrdersByDay(Base):
    """Aggregated sales totals per calendar day."""

    __tablename__ = "orders_by_day"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (Index("ix_orders_by_day_date", "date"),)


class OrdersByWaiter(Base):
    """Aggregated sales totals per waiter and day."""

    __tablename__ = "orders_by_waiter"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    waiter_id: Mapped[int] = mapped_column(ForeignKey("waiters.id"), primary_key=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    waiter: Mapped[Waiter] = relationship(back_populates="daily_sales")

    __table_args__ = (
        Index("ix_orders_by_waiter_date", "date"),
        Index("ix_orders_by_waiter_waiter_id", "waiter_id"),
    )


class OrdersByTable(Base):
    """Aggregated sales totals per table and day."""

    __tablename__ = "orders_by_table"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), primary_key=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    table: Mapped[Table] = relationship(back_populates="daily_sales")

    __table_args__ = (
        Index("ix_orders_by_table_date", "date"),
        Index("ix_orders_by_table_table_id", "table_id"),
    )


__all__ = [
    "Waiter",
    "Table",
    "Category",
    "MenuItem",
    "Order",
    "OrderItem",
    "Ticket",
    "Setting",
    "AuditLog",
    "OrdersByDay",
    "OrdersByWaiter",
    "OrdersByTable",
]
