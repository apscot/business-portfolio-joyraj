"""Profit targets: yearly/quarterly/monthly/weekly cards for an FY (user-scoped)."""
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import fy as fy_mod
from app.db import get_db
from app.models import Investment, User
from app.routers.pnl import fy_expiry_trades
from app.routers.summary import fy_bounds
from app.security import current_user
from app.services import pnl as pnl_service
from app.services import targets as targets_service

router = APIRouter(prefix="/api/targets", tags=["targets"])


class TargetCard(BaseModel):
    period: str
    label: str
    start: date
    end: date
    target: Decimal
    achieved: Decimal
    status: str
    progress: Decimal


@router.get("", response_model=list[TargetCard])
def get_targets(
    fy: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, Any]]:
    start, end = fy_bounds(fy)
    invested = sum(
        db.scalars(
            select(Investment.amount).where(
                Investment.user_id == user.id, Investment.date.between(start, end)
            )
        ),
        Decimal(0),
    )
    rows = pnl_service.by_expiry(fy_expiry_trades(db, user.id, start, end))
    return targets_service.build(invested, rows, fy_mod.fy_of(start), date.today())
