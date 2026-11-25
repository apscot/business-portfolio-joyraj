"""Realised P&L per (underlying, expiry). Pure logic: no HTTP, no DB."""
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

ZERO = Decimal("0")


class TradeLike(Protocol):
    symbol: str
    trade_type: str
    quantity: Decimal
    price: Decimal
    expiry_date: date | None
    underlying: str


def by_expiry(trades: Iterable[TradeLike]) -> list[dict[str, Any]]:
    """Group trades by (underlying, expiry_date) and compute realised P&L.

    pnl = sum(sell qty * price) - sum(buy qty * price). ``open`` is True when the net
    quantity of any symbol in the group is non-zero (P&L is then partial). Trades without an
    expiry date are ignored. Rows are sorted by expiry date, then underlying.
    """
    groups: dict[tuple[date, str], dict[str, Any]] = {}
    for t in trades:
        if t.expiry_date is None:
            continue
        g = groups.setdefault(
            (t.expiry_date, t.underlying), {"pnl": ZERO, "trades": 0, "net": {}}
        )
        value = t.quantity * t.price
        sign = 1 if t.trade_type == "sell" else -1
        g["pnl"] += value * sign
        g["trades"] += 1
        g["net"][t.symbol] = g["net"].get(t.symbol, ZERO) - sign * t.quantity
    return [
        {
            "expiry_date": expiry,
            "underlying": underlying,
            "trades": g["trades"],
            "pnl": g["pnl"].quantize(Decimal("0.01")),
            "open": any(q != 0 for q in g["net"].values()),
        }
        for (expiry, underlying), g in sorted(groups.items())
    ]


def total(rows: Iterable[dict[str, Any]]) -> Decimal:
    """Sum of pnl over rows."""
    return sum((r["pnl"] for r in rows), Decimal("0.00"))
