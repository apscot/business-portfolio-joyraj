"""Tradebook CSV parsing and saving (pure logic: no HTTP)."""
import csv
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, TextIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Trade

COLUMNS = (
    "symbol",
    "isin",
    "trade_date",
    "exchange",
    "segment",
    "series",
    "trade_type",
    "auction",
    "quantity",
    "price",
    "trade_id",
    "order_id",
    "order_execution_time",
    "expiry_date",
)
REQUIRED = ("symbol", "exchange", "segment", "trade_type", "trade_id")
MAX_LEN = {
    "symbol": 100,
    "isin": 20,
    "exchange": 20,
    "segment": 20,
    "series": 20,
    "trade_id": 50,
    "order_id": 50,
}
UNDERLYINGS = ("MIDCPNIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "BANKEX", "NIFTY")
MAX_QTY = Decimal("99999999999999")  # fits Numeric(18, 4)
CHUNK = 500

_LEADING_LETTERS = re.compile(r"^[A-Z]+")
_TRUE = {"true", "yes", "y", "1"}
_FALSE = {"false", "no", "n", "0", ""}


class HeaderError(ValueError):
    """The CSV header does not match the expected columns."""


def derive_underlying(symbol: str) -> str:
    """Underlying index from the symbol prefix (e.g. NIFTY26OCT23500CE -> NIFTY), else OTHER."""
    match = _LEADING_LETTERS.match(symbol.upper())
    if match is not None and match.group(0) in UNDERLYINGS:
        return match.group(0)
    return "OTHER"


def _decimal(raw: str, name: str, allow_zero: bool) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"{name} is not a number") from None
    if not value.is_finite() or value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    if value > MAX_QTY:
        raise ValueError(f"{name} is too large")
    return value


def _date(raw: str, name: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"{name} must be YYYY-MM-DD") from None


def _datetime(raw: str, name: str) -> datetime:
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=None)
    except ValueError:
        raise ValueError(f"{name} must be an ISO date-time") from None


def _validate_row(raw: dict[str, str]) -> dict[str, Any]:
    """Convert one stripped CSV row to Trade fields; raise ValueError with a short reason."""
    for name in REQUIRED:
        if not raw[name]:
            raise ValueError(f"{name} is required")
    for name, limit in MAX_LEN.items():
        if len(raw[name]) > limit:
            raise ValueError(f"{name} is longer than {limit} characters")
    trade_type = raw["trade_type"].lower()
    if trade_type not in ("buy", "sell"):
        raise ValueError("trade_type must be buy or sell")
    auction = raw["auction"].lower()
    if auction not in _TRUE | _FALSE:
        raise ValueError("auction must be true or false")
    expiry = raw["expiry_date"]
    return {
        "symbol": raw["symbol"],
        "isin": raw["isin"],
        "trade_date": _date(raw["trade_date"], "trade_date"),
        "exchange": raw["exchange"],
        "segment": raw["segment"],
        "series": raw["series"],
        "trade_type": trade_type,
        "auction": auction in _TRUE,
        "quantity": _decimal(raw["quantity"], "quantity", allow_zero=False),
        "price": _decimal(raw["price"], "price", allow_zero=True),
        "trade_id": raw["trade_id"],
        "order_id": raw["order_id"],
        "order_execution_time": _datetime(raw["order_execution_time"], "order_execution_time"),
        "expiry_date": _date(expiry, "expiry_date") if expiry else None,
        "underlying": derive_underlying(raw["symbol"]),
    }


def parse_csv(stream: TextIO) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse a tradebook CSV into (valid rows, invalid ``{row, reason}``).

    Headers are whitespace-trimmed and case-insensitive but must match the expected columns
    exactly (any order); otherwise ``HeaderError`` is raised. ``row`` is the 1-based file line
    number (the header is row 1).
    """
    reader = csv.reader(stream)
    header = next(reader, None)
    if header is None:
        raise HeaderError("CSV is empty")
    names = [h.strip().lower() for h in header]
    missing = [c for c in COLUMNS if c not in names]
    unexpected = sorted({n for n in names if n not in COLUMNS})
    if missing or unexpected or len(names) != len(set(names)):
        parts = []
        if missing:
            parts.append("missing columns: " + ", ".join(missing))
        if unexpected:
            parts.append("unexpected columns: " + ", ".join(unexpected[:10]))
        if not parts:
            parts.append("duplicate columns")
        raise HeaderError("Invalid header - " + "; ".join(parts))

    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for cells in reader:
        row_no = reader.line_num
        if not any(c.strip() for c in cells):
            continue
        if len(cells) != len(names):
            reason = f"expected {len(names)} columns, got {len(cells)}"
            invalid.append({"row": row_no, "reason": reason})
            continue
        raw = {n: c.strip() for n, c in zip(names, cells, strict=True)}
        try:
            valid.append(_validate_row(raw))
        except ValueError as exc:
            invalid.append({"row": row_no, "reason": str(exc)})
    return valid, invalid


def save(session: Session, user_id: int, rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Insert rows whose ``trade_id`` is new for this user; return (inserted, duplicates).

    Existing trades (and repeats within ``rows``) are skipped, never updated.
    """
    ids = list({r["trade_id"] for r in rows})
    seen: set[str] = set()
    for i in range(0, len(ids), CHUNK):
        stmt = select(Trade.trade_id).where(
            Trade.user_id == user_id, Trade.trade_id.in_(ids[i : i + CHUNK])
        )
        seen.update(session.scalars(stmt))
    inserted = 0
    for row in rows:
        if row["trade_id"] in seen:
            continue
        seen.add(row["trade_id"])
        session.add(Trade(user_id=user_id, **row))
        inserted += 1
    session.commit()
    return inserted, len(rows) - inserted
