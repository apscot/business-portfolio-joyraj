from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Trade
from app.services import pnl, targets


@dataclass
class T:
    symbol: str
    trade_type: str
    quantity: Decimal
    price: Decimal
    expiry_date: date | None
    underlying: str = "NIFTY"


def _t(sym: str, side: str, qty: str, price: str, expiry: str | None, und: str = "NIFTY") -> T:
    return T(sym, side, Decimal(qty), Decimal(price), date.fromisoformat(expiry) if expiry else None, und)


# --- pnl service ---
def test_by_expiry_closed_and_open() -> None:
    trades = [
        _t("N23500CE", "buy", "520", "101.5", "2026-10-27"),
        _t("N23500CE", "sell", "520", "120.25", "2026-10-27"),
        _t("S80000PE", "sell", "455", "88", "2026-10-28", "SENSEX"),
        _t("N22000CE", "buy", "50", "10", "2026-03-26"),
        _t("N22000CE", "sell", "20", "12", "2026-03-26"),
        _t("FUT", "buy", "1", "5", None, "OTHER"),
    ]
    rows = pnl.by_expiry(trades)
    assert [(r["expiry_date"], r["underlying"]) for r in rows] == [
        (date(2026, 3, 26), "NIFTY"),
        (date(2026, 10, 27), "NIFTY"),
        (date(2026, 10, 28), "SENSEX"),
    ]
    assert [r["pnl"] for r in rows] == [Decimal("-260.00"), Decimal("9750.00"), Decimal("40040.00")]
    assert [r["open"] for r in rows] == [True, False, True]
    assert [r["trades"] for r in rows] == [2, 2, 1]
    assert pnl.total(rows) == Decimal("49530.00")


def test_by_expiry_empty() -> None:
    assert pnl.by_expiry([]) == []
    assert pnl.total([]) == Decimal("0.00")


# --- targets service ---
def test_period_bounds_current_fy() -> None:
    b = targets.period_bounds("2026-27", date(2026, 10, 15))  # a Thursday
    assert b["yearly"] == (date(2026, 4, 1), date(2027, 3, 31))
    assert b["quarterly"] == (date(2026, 10, 1), date(2026, 12, 31))
    assert b["monthly"] == (date(2026, 10, 1), date(2026, 10, 31))
    assert b["weekly"] == (date(2026, 10, 12), date(2026, 10, 18))


def test_period_bounds_quarter_in_next_calendar_year() -> None:
    b = targets.period_bounds("2026-27", date(2027, 2, 10))
    assert b["quarterly"] == (date(2027, 1, 1), date(2027, 3, 31))
    assert b["monthly"] == (date(2027, 2, 1), date(2027, 2, 28))


def test_period_bounds_past_and_future_fy_clamp() -> None:
    past = targets.period_bounds("2020-21", date(2026, 10, 15))
    assert past["quarterly"] == (date(2021, 1, 1), date(2021, 3, 31))
    assert past["monthly"] == (date(2021, 3, 1), date(2021, 3, 31))
    assert past["weekly"] == (date(2021, 3, 29), date(2021, 3, 31))  # clipped to FY end
    future = targets.period_bounds("2030-31", date(2026, 10, 15))
    assert future["quarterly"] == (date(2030, 4, 1), date(2030, 6, 30))
    assert future["weekly"] == (date(2030, 4, 1), date(2030, 4, 7))  # clipped to FY start


def test_status_and_progress() -> None:
    t = Decimal("100")
    assert targets.status_of(t, Decimal("100")) == "Met"
    assert targets.status_of(t, Decimal("150")) == "Met"
    assert targets.status_of(t, Decimal("40")) == "In progress"
    assert targets.status_of(t, Decimal("0")) == "Behind"
    assert targets.status_of(t, Decimal("-5")) == "Behind"
    assert targets.status_of(Decimal("0"), Decimal("0")) == "Behind"
    assert targets.progress_of(t, Decimal("40")) == Decimal("40.00")
    assert targets.progress_of(t, Decimal("250")) == Decimal("100.00")
    assert targets.progress_of(t, Decimal("-10")) == Decimal("0.00")
    assert targets.progress_of(Decimal("0"), Decimal("5")) == Decimal("100.00")
    assert targets.progress_of(Decimal("0"), Decimal("-5")) == Decimal("0.00")


def test_build_targets_and_achieved() -> None:
    rows = [
        {"expiry_date": date(2026, 10, 13), "pnl": Decimal("1000.00")},  # week, month, quarter
        {"expiry_date": date(2026, 10, 27), "pnl": Decimal("9000.00")},  # month, quarter
        {"expiry_date": date(2026, 11, 3), "pnl": Decimal("20000.00")},  # quarter only
        {"expiry_date": date(2026, 5, 5), "pnl": Decimal("-500.00")},  # year only
    ]
    cards = {c["period"]: c for c in targets.build(Decimal("1000000"), rows, "2026-27", date(2026, 10, 15))}
    assert list(cards) == ["yearly", "quarterly", "monthly", "weekly"]
    assert cards["yearly"]["target"] == Decimal("100000.00")
    assert cards["quarterly"]["target"] == Decimal("25000.00")
    assert cards["monthly"]["target"] == Decimal("8333.33")
    assert cards["weekly"]["target"] == Decimal("1923.08")
    assert cards["yearly"]["achieved"] == Decimal("29500.00")
    assert cards["quarterly"]["achieved"] == Decimal("30000.00")
    assert cards["monthly"]["achieved"] == Decimal("10000.00")
    assert cards["weekly"]["achieved"] == Decimal("1000.00")
    assert cards["yearly"]["status"] == "In progress"
    assert cards["yearly"]["progress"] == Decimal("29.50")
    assert cards["quarterly"]["status"] == "Met"
    assert cards["monthly"]["status"] == "Met"
    assert cards["weekly"]["status"] == "In progress"
    assert cards["weekly"]["progress"] == Decimal("52.00")
    assert cards["quarterly"]["label"].startswith("Q3")


def test_build_with_no_data_is_behind() -> None:
    cards = targets.build(Decimal("0"), [], "2026-27", date(2026, 10, 15))
    assert all(c["target"] == 0 and c["status"] == "Behind" and c["progress"] == 0 for c in cards)


# --- routers ---
def _auth(client: TestClient, email: str) -> dict[str, str]:
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _user_id(client: TestClient, headers: dict[str, str]) -> int:
    return int(client.get("/api/auth/me", headers=headers).json()["id"])


def _add(db: Session, uid: int, tid: str, sym: str, side: str, qty: str, price: str,
         expiry: str, und: str = "NIFTY") -> None:
    e = date.fromisoformat(expiry)
    db.add(
        Trade(
            user_id=uid, symbol=sym, trade_date=e, exchange="NSE", segment="FO", trade_type=side,
            quantity=Decimal(qty), price=Decimal(price), trade_id=tid,
            order_execution_time=datetime(e.year, e.month, e.day, 10), expiry_date=e, underlying=und,
        )
    )
    db.commit()


@pytest.mark.parametrize("path", ["/api/pnl", "/api/targets"])
def test_requires_auth(client: TestClient, path: str) -> None:
    assert client.get(path).status_code in (401, 403)


@pytest.mark.parametrize("path", ["/api/pnl", "/api/targets"])
def test_invalid_fy_rejected(client: TestClient, path: str) -> None:
    h = _auth(client, "a@example.com")
    assert client.get(path, params={"fy": "2026"}, headers=h).status_code == 422


def test_pnl_endpoint_filter_fy_and_isolation(client: TestClient, db_session: Session) -> None:
    alice = _auth(client, "alice@example.com")
    bob = _auth(client, "bob@example.com")
    a, b = _user_id(client, alice), _user_id(client, bob)
    _add(db_session, a, "1", "N1", "buy", "10", "100", "2026-10-27")
    _add(db_session, a, "2", "N1", "sell", "10", "130", "2026-10-27")
    _add(db_session, a, "3", "S1", "sell", "5", "50", "2026-10-28", "SENSEX")
    _add(db_session, a, "4", "N0", "sell", "1", "1", "2025-10-28")  # other FY
    _add(db_session, b, "1", "N1", "sell", "10", "999", "2026-10-27")  # other user

    body = client.get("/api/pnl", params={"fy": "2026-27"}, headers=alice).json()
    assert body["fy"] == "2026-27"
    assert [(r["underlying"], r["pnl"], r["open"], r["trades"]) for r in body["rows"]] == [
        ("NIFTY", "300.00", False, 2),
        ("SENSEX", "250.00", True, 1),
    ]
    assert Decimal(body["total"]) == Decimal("550.00")

    only = client.get("/api/pnl", params={"fy": "2026-27", "underlying": "SENSEX"}, headers=alice).json()
    assert [r["underlying"] for r in only["rows"]] == ["SENSEX"]
    assert client.get("/api/pnl", params={"underlying": "OTHER"}, headers=alice).status_code == 422

    bob_body = client.get("/api/pnl", params={"fy": "2026-27"}, headers=bob).json()
    assert [r["pnl"] for r in bob_body["rows"]] == ["9990.00"]


def test_targets_endpoint_past_fy(client: TestClient, db_session: Session) -> None:
    h = _auth(client, "alice@example.com")
    uid = _user_id(client, h)
    client.post("/api/investments", json={"date": "2020-06-01", "amount": "120000"}, headers=h)
    _add(db_session, uid, "1", "N1", "buy", "10", "100", "2021-03-25")
    _add(db_session, uid, "2", "N1", "sell", "10", "130", "2021-03-25")  # +300 in last period

    r = client.get("/api/targets", params={"fy": "2020-21"}, headers=h)
    assert r.status_code == 200
    cards = {c["period"]: c for c in r.json()}
    assert Decimal(cards["yearly"]["target"]) == Decimal("12000.00")
    assert Decimal(cards["quarterly"]["target"]) == Decimal("3000.00")
    assert Decimal(cards["monthly"]["target"]) == Decimal("1000.00")
    assert Decimal(cards["weekly"]["target"]) == Decimal("230.77")
    assert Decimal(cards["quarterly"]["achieved"]) == Decimal("300.00")
    assert cards["quarterly"]["status"] == "In progress"
    assert Decimal(cards["quarterly"]["progress"]) == Decimal("10.00")
    assert cards["yearly"]["start"] == "2020-04-01"

    other = _auth(client, "bob@example.com")
    bob_cards = client.get("/api/targets", params={"fy": "2020-21"}, headers=other).json()
    assert all(Decimal(c["target"]) == 0 and c["status"] == "Behind" for c in bob_cards)
