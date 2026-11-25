"""Financial-year list and summary (totals + growth series). Wired in via routers/investments.py."""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import fy as fy_mod
from app.db import get_db
from app.models import Holding, Interest, Investment, Trade, User
from app.security import current_user

router = APIRouter(tags=["summary"])

ZERO = Decimal("0.00")


def fy_bounds(fy: str | None) -> tuple[date, date]:
    """Resolve the ``fy`` query parameter (default: current FY); 422 if malformed."""
    try:
        return fy_mod.fy_range(fy if fy is not None else fy_mod.current_fy())
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid financial year") from None


class GrowthPoint(BaseModel):
    date: date
    invested: Decimal
    total: Decimal


class Summary(BaseModel):
    fy: str
    invested: Decimal
    interest: Decimal
    total: Decimal
    holdings: Decimal
    series: list[GrowthPoint]


@router.get("/fy", response_model=list[str])
def list_fys(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[str]:
    dates: list[date] = []
    for column, model in (
        (Holding.as_of_date, Holding),
        (Interest.date, Interest),
        (Investment.date, Investment),
        (Trade.trade_date, Trade),
    ):
        dates.extend(db.scalars(select(column).where(model.user_id == user.id).distinct()))
    return fy_mod.list_fys(dates)


@router.get("/summary", response_model=Summary)
def summary(
    fy: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Summary:
    start, end = fy_bounds(fy)
    invested_rows = db.execute(
        select(Investment.date, Investment.amount).where(
            Investment.user_id == user.id, Investment.date.between(start, end)
        )
    ).all()
    interest_rows = db.execute(
        select(Interest.date, Interest.amount).where(
            Interest.user_id == user.id, Interest.date.between(start, end)
        )
    ).all()
    holdings = sum(
        db.scalars(
            select(Holding.amount).where(
                Holding.user_id == user.id, Holding.as_of_date.between(start, end)
            )
        ),
        ZERO,
    )

    per_day: dict[date, tuple[Decimal, Decimal]] = {}
    for d, amount in invested_rows:
        inv, intr = per_day.get(d, (ZERO, ZERO))
        per_day[d] = (inv + amount, intr)
    for d, amount in interest_rows:
        inv, intr = per_day.get(d, (ZERO, ZERO))
        per_day[d] = (inv, intr + amount)

    series: list[GrowthPoint] = []
    invested = interest = ZERO
    for d in sorted(per_day):
        invested += per_day[d][0]
        interest += per_day[d][1]
        series.append(GrowthPoint(date=d, invested=invested, total=invested + interest))
    return Summary(
        fy=fy_mod.fy_of(start),
        invested=invested,
        interest=interest,
        total=invested + interest,
        holdings=holdings,
        series=series,
    )
