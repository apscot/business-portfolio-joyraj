from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.security import ALGORITHM, create_access_token

CREDS = {"email": "Trader@Example.com", "password": "correct-horse"}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_token_and_me_works(client: TestClient) -> None:
    r = client.post("/api/auth/register", json=CREDS)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    me = client.get("/api/auth/me", headers=_auth(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "trader@example.com"
    assert "password" not in me.text


def test_token_expires_in_8_hours(client: TestClient) -> None:
    token = client.post("/api/auth/register", json=CREDS).json()["access_token"]
    p = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    assert p["exp"] - p["iat"] == 8 * 3600


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=CREDS).status_code == 201
    r = client.post("/api/auth/register", json={**CREDS, "email": "trader@example.com"})
    assert r.status_code == 409


def test_register_validation(client: TestClient) -> None:
    assert client.post("/api/auth/register", json={**CREDS, "password": "short"}).status_code == 422
    assert client.post("/api/auth/register", json={**CREDS, "email": "nope"}).status_code == 422
    long_bytes = {**CREDS, "password": "é" * 40}  # 80 bytes, 40 chars
    assert client.post("/api/auth/register", json=long_bytes).status_code == 422


def test_login_success(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    r = client.post("/api/auth/login", json=CREDS)
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=_auth(r.json()["access_token"])).status_code == 200


def test_login_bad_password(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    r = client.post("/api/auth/login", json={**CREDS, "password": "wrong-password"})
    assert r.status_code == 401


def test_login_unknown_user(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"email": "no@one.com", "password": "whatever123"})
    assert r.status_code == 401


def test_login_overlong_password_rejected(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    r = client.post("/api/auth/login", json={**CREDS, "password": "é" * 40})
    assert r.status_code == 401


def test_protected_route_requires_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=_auth("garbage")).status_code == 401


def test_expired_and_forged_tokens_rejected(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    secret = get_settings().jwt_secret
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    expired = jwt.encode({"sub": "1", "exp": past}, secret, algorithm=ALGORITHM)
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "x" * 40,
        algorithm=ALGORITHM,
    )
    assert client.get("/api/auth/me", headers=_auth(expired)).status_code == 401
    assert client.get("/api/auth/me", headers=_auth(forged)).status_code == 401


def test_token_for_missing_user_rejected(client: TestClient) -> None:
    assert client.get("/api/auth/me", headers=_auth(create_access_token(999))).status_code == 401
