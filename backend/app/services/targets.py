"""Profit targets: 10% of invested value per FY, split into quarter/month/week. Pure logic."""
import calendar
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app import fy as fy_mod

YEARLY_RATE = Decimal("0.10")
CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def reference_date(fy: str, today: date) -> date:
    """Day that defines 'current' periods: today clamped into the FY (past FY -> its last day)."""
    start, end = fy_mod.fy_range(fy)
    return min(max(today, start), end)


def period_bounds(fy: str, today: date) -> dict[str, tuple[date, date]]:
    """Inclusive (first, last) day of the current year/quarter/month/week, clipped to the FY."""
    start, end = fy_mod.fy_range(fy)
    ref = reference_date(fy, today)
    q = ((ref.month - 4) % 12) // 3
    q_month = 4 + 3 * q
    q_year = start.year if q_month <= 12 else start.year + 1
    q_month = (q_month - 1) % 12 + 1
    q_start = date(q_year, q_month, 1)
    last_month = q_month + 2
    q_end = date(q_year, last_month, calendar.monthrange(q_year, last_month)[1])
    m_start = ref.replace(day=1)
    m_end = ref.replace(day=calendar.monthrange(ref.year, ref.month)[1])
    w_start = ref - timedelta(days=ref.weekday())
    w_end = w_start + timedelta(days=6)
    return {
        "yearly": (start, end),
        "quarterly": (q_start, q_end),
        "monthly": (m_start, m_end),
        "weekly": (max(w_start, start), min(w_end, end)),
    }


def status_of(target: Decimal, achieved: Decimal) -> str:
    """Met (achieved >= target, and positive), In progress (> 0), else Behind."""
    if achieved > 0 and achieved >= target:
        return "Met"
    if achieved > 0:
        return "In progress"
    return "Behind"


def progress_of(target: Decimal, achieved: Decimal) -> Decimal:
    """Percentage of target achieved, clamped to 0..100."""
    if target <= 0:
        return Decimal("100.00") if achieved > 0 else Decimal("0.00")
    pct = achieved / target * 100
    return _money(min(max(pct, Decimal(0)), Decimal(100)))


def _label(period: str, first: date, last: date, fy: str) -> str:
    if period == "yearly":
        return f"FY {fy}"
    if period == "quarterly":
        q = ((first.month - 4) % 12) // 3 + 1
        return f"Q{q} ({first:%b} – {last:%b %Y})"
    if period == "monthly":
        return f"{first:%B %Y}"
    return f"Week {first:%d %b} – {last:%d %b %Y}"


def build(
    invested: Decimal,
    pnl_by_expiry: Iterable[dict[str, Any]],
    fy: str,
    today: date,
) -> list[dict[str, Any]]:
    """Four target cards (yearly, quarterly, monthly, weekly) for the current period of ``fy``.

    ``achieved`` is the realised P&L of expiries falling inside the period.
    """
    rows = list(pnl_by_expiry)
    yearly = invested * YEARLY_RATE
    divisors = {"yearly": 1, "quarterly": 4, "monthly": 12, "weekly": 52}
    cards: list[dict[str, Any]] = []
    for period, (first, last) in period_bounds(fy, today).items():
        target = _money(yearly / divisors[period])
        achieved = _money(
            sum((r["pnl"] for r in rows if first <= r["expiry_date"] <= last), Decimal(0))
        )
        cards.append(
            {
                "period": period,
                "label": _label(period, first, last, fy),
                "start": first,
                "end": last,
                "target": target,
                "achieved": achieved,
                "status": status_of(target, achieved),
                "progress": progress_of(target, achieved),
            }
        )
    return cards
