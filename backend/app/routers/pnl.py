"""Realised P&L per expiry (user-scoped, FY-filtered by expiry date)."""
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import fy as fy_mod
from app.db import get_db
from app.models import Trade, User
from app.routers.summary import fy_bounds
from app.security import current_user
from app.services import pnl as pnl_service

router = APIRouter(prefix="/api/pnl", tags=["pnl"])


class PnlRow(BaseModel):
    expiry_date: date
    underlying: str
    trades: int
    pnl: Decimal
    open: bool


class PnlOut(BaseModel):
    fy: str
    rows: list[PnlRow]
    total: Decimal


def fy_expiry_trades(db: Session, user_id: int, start: date, end: date) -> list[Trade]:
    """The user's trades whose expiry falls inside [start, end]."""
    stmt = select(Trade).where(
        Trade.user_id == user_id, Trade.expiry_date.between(start, end)
    )
    return list(db.scalars(stmt))


@router.get("", response_model=PnlOut)
def get_pnl(
    fy: str | None = Query(default=None),
    underlying: Literal["NIFTY", "SENSEX"] | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> PnlOut:
    start, end = fy_bounds(fy)
    trades = fy_expiry_trades(db, user.id, start, end)
    if underlying is not None:
        trades = [t for t in trades if t.underlying == underlying]
    rows = pnl_service.by_expiry(trades)
    return PnlOut(
        fy=fy_mod.fy_of(start),
        rows=[PnlRow(**r) for r in rows],
        total=pnl_service.total(rows),
    )
