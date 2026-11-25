import io

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Trade
from app.routers import trades as trades_router
from app.services import trade_import

# Sample tradebook; note the stray tab after "auction" in the header (must be trimmed).
HEADER = (
    "symbol,isin,trade_date,exchange,segment,series,trade_type,auction\t,quantity,price,"
    "trade_id,order_id,order_execution_time,expiry_date"
)
SAMPLE = "\n".join(
    [
        HEADER,
        "NIFTY26OCT23500CE,,2026-10-01,NSE,FO,,buy,false,520,101.5,T1,O1,2026-10-01T09:20:15,2026-10-27",
        "NIFTY26OCT23500CE,,2026-10-05,NSE,FO,,sell,false,520,120.25,T2,O2,2026-10-05T10:00:00,2026-10-27",
        "SENSEX26OCT80000PE,,2026-10-06,BSE,FO,,sell,false,455,88,T3,O3,2026-10-06T11:30:00,2026-10-28",
        "NIFTY25MAR22000CE,,2026-03-20,NSE,FO,,buy,false,50,10,T4,O4,2026-03-20T09:16:00,2026-03-27",
        "RELIANCE26OCTFUT,,2026-10-07,NSE,FO,,buy,false,250,1400.55,T5,O5,2026-10-07T09:30:00,",
    ]
)


def _auth(client: TestClient, email: str) -> dict[str, str]:
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload(client: TestClient, headers: dict[str, str], content: str | bytes) -> httpx.Response:
    data = content.encode() if isinstance(content, str) else content
    return client.post(
        "/api/trades/upload", files={"file": ("t.csv", data, "text/csv")}, headers=headers
    )


# --- service ---
def test_parse_csv_valid_sample() -> None:
    valid, invalid = trade_import.parse_csv(io.StringIO(SAMPLE))
    assert invalid == []
    assert [r["underlying"] for r in valid] == ["NIFTY", "NIFTY", "SENSEX", "NIFTY", "OTHER"]
    assert str(valid[0]["quantity"]) == "520"
    assert valid[4]["expiry_date"] is None


def test_parse_csv_rejects_bad_header() -> None:
    with pytest.raises(trade_import.HeaderError, match="missing columns"):
        trade_import.parse_csv(io.StringIO("symbol,price\nX,1\n"))
    with pytest.raises(trade_import.HeaderError, match="unexpected columns"):
        trade_import.parse_csv(io.StringIO(HEADER + ",extra\n"))
    with pytest.raises(trade_import.HeaderError, match="duplicate"):
        trade_import.parse_csv(io.StringIO(HEADER + ",symbol\n"))
    with pytest.raises(trade_import.HeaderError, match="empty"):
        trade_import.parse_csv(io.StringIO(""))


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ("S,,2026-10-01,NSE,FO,,hold,false,1,1,T,O,2026-10-01T09:00:00,", "trade_type"),
        ("S,,01/10/2026,NSE,FO,,buy,false,1,1,T,O,2026-10-01T09:00:00,", "trade_date"),
        ("S,,2026-10-01,NSE,FO,,buy,maybe,1,1,T,O,2026-10-01T09:00:00,", "auction"),
        ("S,,2026-10-01,NSE,FO,,buy,false,abc,1,T,O,2026-10-01T09:00:00,", "quantity"),
        ("S,,2026-10-01,NSE,FO,,buy,false,0,1,T,O,2026-10-01T09:00:00,", "quantity"),
        ("S,,2026-10-01,NSE,FO,,buy,false,1,-1,T,O,2026-10-01T09:00:00,", "price"),
        ("S,,2026-10-01,NSE,FO,,buy,false,1,NaN,T,O,2026-10-01T09:00:00,", "price"),
        ("S,,2026-10-01,NSE,FO,,buy,false,1e30,1,T,O,2026-10-01T09:00:00,", "too large"),
        ("S,,2026-10-01,NSE,FO,,buy,false,1,1,,O,2026-10-01T09:00:00,", "trade_id is required"),
        ("S,,2026-10-01,NSE,FO,,buy,false,1,1,T,O,yesterday,", "order_execution_time"),
        ("S,,2026-10-01,NSE,FO,,buy,false,1,1,T,O,2026-10-01T09:00:00,soon", "expiry_date"),
        ("S,,2026-10-01,NSE,FO,,buy,false,1,1," + "T" * 51 + ",O,2026-10-01T09:00:00,", "longer"),
        ("S,,2026-10-01", "expected 14 columns"),
    ],
)
def test_parse_csv_invalid_rows(row: str, reason: str) -> None:
    valid, invalid = trade_import.parse_csv(io.StringIO(HEADER + "\n\n" + row + "\n"))
    assert valid == []
    assert len(invalid) == 1
    assert invalid[0]["row"] == 3
    assert reason in invalid[0]["reason"]


def test_save_skips_duplicates_and_is_user_scoped(db_session: Session) -> None:
    rows, _ = trade_import.parse_csv(io.StringIO(SAMPLE))
    assert trade_import.save(db_session, 1, rows + rows[:2]) == (5, 2)
    assert trade_import.save(db_session, 1, rows) == (0, 5)
    assert trade_import.save(db_session, 2, rows) == (5, 0)  # other user may reuse trade ids


def test_save_never_updates_existing(db_session: Session) -> None:
    rows, _ = trade_import.parse_csv(io.StringIO(SAMPLE))
    trade_import.save(db_session, 1, rows[:1])
    changed = [{**rows[0], "price": rows[0]["price"] + 1}]
    assert trade_import.save(db_session, 1, changed) == (0, 1)
    price = db_session.scalar(select(Trade.price).where(Trade.trade_id == "T1"))
    assert price == rows[0]["price"]


# --- API ---
def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/trades").status_code == 401
    r = client.post("/api/trades/upload", files={"file": ("t.csv", b"x", "text/csv")})
    assert r.status_code == 401


def test_upload_then_reupload_is_idempotent(client: TestClient, db_session: Session) -> None:
    h = _auth(client, "a@example.com")
    first = _upload(client, h, SAMPLE)
    assert first.status_code == 200
    assert first.json() == {"inserted": 5, "duplicates": 0, "invalid": []}
    again = _upload(client, h, SAMPLE)
    assert again.json() == {"inserted": 0, "duplicates": 5, "invalid": []}
    assert db_session.scalar(select(func.count()).select_from(Trade)) == 5


def test_upload_reports_invalid_rows(client: TestClient) -> None:
    h = _auth(client, "a@example.com")
    bad = SAMPLE + "\nBAD,,2026-10-01,NSE,FO,,hold,false,1,1,T9,O,2026-10-01T09:00:00,"
    body = _upload(client, h, "\ufeff" + bad).json()
    assert body["inserted"] == 5
    assert body["invalid"] == [{"row": 7, "reason": "trade_type must be buy or sell"}]


def test_upload_rejects_bad_files(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _auth(client, "a@example.com")
    assert _upload(client, h, "a,b\n1,2\n").status_code == 400
    assert _upload(client, h, b"\xff\xfe\x00bad").status_code == 400
    monkeypatch.setattr(trades_router, "MAX_UPLOAD_BYTES", 10)
    assert _upload(client, h, SAMPLE).status_code == 413


def test_list_paginates_filters_fy_and_isolates_users(client: TestClient) -> None:
    alice = _auth(client, "a@example.com")
    bob = _auth(client, "b@example.com")
    extra = "\n".join(
        f"NIFTY26OCT23500CE,,2026-10-10,NSE,FO,,buy,false,1,1,X{i},O,2026-10-10T09:{i:02d}:00,"
        for i in range(20)
    )
    _upload(client, alice, SAMPLE + "\n" + extra)

    p1 = client.get("/api/trades", params={"fy": "2026-27"}, headers=alice).json()
    assert p1["total"] == 24  # T4 (Mar 2026) belongs to FY 2025-26
    assert (p1["page"], p1["page_size"], len(p1["items"])) == (1, 15, 15)
    times = [i["order_execution_time"] for i in p1["items"]]
    assert times == sorted(times, reverse=True)
    p2 = client.get("/api/trades", params={"fy": "2026-27", "page": 2}, headers=alice).json()
    assert len(p2["items"]) == 9
    assert not {i["id"] for i in p1["items"]} & {i["id"] for i in p2["items"]}
    assert p1["items"][0]["underlying"] == "NIFTY" and p1["items"][0]["quantity"] is not None

    old = client.get("/api/trades", params={"fy": "2025-26"}, headers=alice).json()
    assert [i["trade_id"] for i in old["items"]] == ["T4"]

    other = client.get("/api/trades", params={"fy": "2026-27"}, headers=bob).json()
    assert other["total"] == 0 and other["items"] == []


@pytest.mark.parametrize("params", [{"fy": "bad"}, {"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_list_validates_params(client: TestClient, params: dict[str, object]) -> None:
    h = _auth(client, "a@example.com")
    assert client.get("/api/trades", params=params, headers=h).status_code == 422
