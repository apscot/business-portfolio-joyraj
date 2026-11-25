"""SQLAlchemy models. Every data row carries an indexed ``user_id``; money is Numeric."""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

MONEY = Numeric(18, 2)
QTY = Numeric(18, 4)
PRICE = Numeric(18, 4)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))  # gsec | mutual_fund | other
    amount: Mapped[Decimal] = mapped_column(MONEY)
    as_of_date: Mapped[date] = mapped_column(Date)


class Interest(Base):
    __tablename__ = "interest"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    note: Mapped[str] = mapped_column(String(500), default="")


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    note: Mapped[str] = mapped_column(String(500), default="")


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        UniqueConstraint("user_id", "trade_id", name="uq_trades_user_trade_id"),
        Index("ix_trades_user_trade_date", "user_id", "trade_date"),
        Index("ix_trades_user_expiry_date", "user_id", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(100))
    isin: Mapped[str] = mapped_column(String(20), default="")
    trade_date: Mapped[date] = mapped_column(Date)
    exchange: Mapped[str] = mapped_column(String(20))
    segment: Mapped[str] = mapped_column(String(20))
    series: Mapped[str] = mapped_column(String(20), default="")
    trade_type: Mapped[str] = mapped_column(String(4))  # buy | sell
    auction: Mapped[bool] = mapped_column(Boolean, default=False)
    quantity: Mapped[Decimal] = mapped_column(QTY)
    price: Mapped[Decimal] = mapped_column(PRICE)
    trade_id: Mapped[str] = mapped_column(String(50))
    order_id: Mapped[str] = mapped_column(String(50), default="")
    order_execution_time: Mapped[datetime] = mapped_column(DateTime)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    underlying: Mapped[str] = mapped_column(String(20), default="OTHER")
