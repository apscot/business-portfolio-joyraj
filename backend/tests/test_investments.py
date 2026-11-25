from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.fy import current_fy


def _headers(client: TestClient, email: str) -> dict[str, str]:
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def alice(client: TestClient) -> dict[str, str]:
    return _headers(client, "alice@example.com")


@pytest.fixture()
def bob(client: TestClient) -> dict[str, str]:
    return _headers(client, "bob@example.com")


HOLDING = {"name": "GSEC 2030", "kind": "gsec", "amount": "1000.50", "as_of_date": "2025-05-10"}
ENTRY = {"date": "2025-05-10", "amount": "500.25", "note": "n"}


@pytest.mark.parametrize("path", ["holdings", "interest", "investments", "summary", "fy"])
def test_requires_auth(client: TestClient, path: str) -> None:
    assert client.get(f"/api/{path}").status_code == 401


@pytest.mark.parametrize(
    ("path", "body"), [("holdings", HOLDING), ("interest", ENTRY), ("investments", ENTRY)]
)
def test_crud_fy_filter_and_isolation(
    client: TestClient, alice: dict[str, str], bob: dict[str, str], path: str, body: dict[str, str]
) -> None:
    url = f"/api/{path}"
    created = client.post(url, json=body, headers=alice)
    assert created.status_code == 201
    item_id = created.json()["id"]
    other_fy_body = {k: ("2024-01-15" if k in ("date", "as_of_date") else v) for k, v in body.items()}
    assert client.post(url, json=other_fy_body, headers=alice).status_code == 201

    in_fy = client.get(url, params={"fy": "2025-26"}, headers=alice).json()
    assert [r["id"] for r in in_fy] == [item_id]
    assert in_fy[0]["amount"] in ("1000.50", "500.25")
    assert len(client.get(url, params={"fy": "2023-24"}, headers=alice).json()) == 1
    assert client.get(url, params={"fy": "2020-21"}, headers=alice).json() == []

    # Bob sees nothing and cannot delete Alice's row.
    assert client.get(url, params={"fy": "2025-26"}, headers=bob).json() == []
    assert client.delete(f"{url}/{item_id}", headers=bob).status_code == 404
    assert len(client.get(url, params={"fy": "2025-26"}, headers=alice).json()) == 1

    assert client.delete(f"{url}/{item_id}", headers=alice).status_code == 204
    assert client.get(url, params={"fy": "2025-26"}, headers=alice).json() == []
    assert client.delete(f"{url}/{item_id}", headers=alice).status_code == 404


def test_default_fy_is_current(client: TestClient, alice: dict[str, str]) -> None:
    body = {**ENTRY, "date": date.today().isoformat()}
    client.post("/api/investments", json=body, headers=alice)
    client.post("/api/investments", json={**ENTRY, "date": "2000-05-01"}, headers=alice)
    assert len(client.get("/api/investments", headers=alice).json()) == 1
    assert client.get("/api/summary", headers=alice).json()["fy"] == current_fy()


@pytest.mark.parametrize("path", ["holdings", "interest", "investments"])
def test_invalid_input_rejected(client: TestClient, alice: dict[str, str], path: str) -> None:
    url = f"/api/{path}"
    assert client.get(url, params={"fy": "2025-27"}, headers=alice).status_code == 422
    assert client.get(url, params={"fy": "bogus"}, headers=alice).status_code == 422
    base = HOLDING if path == "holdings" else ENTRY
    assert client.post(url, json={**base, "amount": "-1"}, headers=alice).status_code == 422
    assert client.post(url, json={**base, "amount": "0"}, headers=alice).status_code == 422
    assert client.post(url, json={**base, "amount": "abc"}, headers=alice).status_code == 422
    assert client.post(url, json={}, headers=alice).status_code == 422


def test_holding_kind_validated(client: TestClient, alice: dict[str, str]) -> None:
    r = client.post("/api/holdings", json={**HOLDING, "kind": "crypto"}, headers=alice)
    assert r.status_code == 422


def test_summary_totals_and_growth_series(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
) -> None:
    for d, amt in [("2025-04-10", "1000"), ("2025-04-10", "500"), ("2025-06-01", "2000")]:
        client.post("/api/investments", json={"date": d, "amount": amt}, headers=alice)
    client.post("/api/interest", json={"date": "2025-05-01", "amount": "50.5"}, headers=alice)
    client.post("/api/holdings", json=HOLDING, headers=alice)
    # Outside FY and other user: excluded.
    client.post("/api/investments", json={"date": "2024-03-31", "amount": "9999"}, headers=alice)
    client.post("/api/investments", json={"date": "2025-04-10", "amount": "7777"}, headers=bob)

    body = client.get("/api/summary", params={"fy": "2025-26"}, headers=alice).json()
    assert body["fy"] == "2025-26"
    assert (body["invested"], body["interest"], body["total"]) == ("3500.00", "50.50", "3550.50")
    assert body["holdings"] == "1000.50"
    assert body["series"] == [
        {"date": "2025-04-10", "invested": "1500.00", "total": "1500.00"},
        {"date": "2025-05-01", "invested": "1500.00", "total": "1550.50"},
        {"date": "2025-06-01", "invested": "3500.00", "total": "3550.50"},
    ]

    empty = client.get("/api/summary", params={"fy": "2025-26"}, headers=bob).json()
    assert empty["invested"] == "7777.00"
    assert empty["series"] == [
        {"date": "2025-04-10", "invested": "7777.00", "total": "7777.00"}
    ]
    assert client.get("/api/summary", params={"fy": "x"}, headers=alice).status_code == 422


def test_summary_empty_fy(client: TestClient, alice: dict[str, str]) -> None:
    body = client.get("/api/summary", params={"fy": "2010-11"}, headers=alice).json()
    assert body["series"] == []
    assert body["total"] == "0.00"


def test_fy_list_user_scoped_and_includes_current(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
) -> None:
    client.post("/api/investments", json={"date": "2023-05-01", "amount": "1"}, headers=alice)
    client.post("/api/interest", json={"date": "2024-02-01", "amount": "1"}, headers=alice)
    client.post("/api/holdings", json={**HOLDING, "as_of_date": "2021-04-01"}, headers=alice)
    client.post("/api/investments", json={"date": "2015-05-01", "amount": "1"}, headers=bob)
    fys = client.get("/api/fy", headers=alice).json()
    assert fys == sorted({current_fy(), "2023-24", "2021-22"}, reverse=True)
    assert "2015-16" not in fys
    assert client.get("/api/fy", headers=bob).json() == sorted({current_fy(), "2015-16"}, reverse=True)
