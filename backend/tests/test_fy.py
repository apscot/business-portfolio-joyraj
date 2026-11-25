from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import fy, models, schemas


def test_fy_range() -> None:
    assert fy.fy_range("2026-27") == (date(2026, 4, 1), date(2027, 3, 31))
    assert fy.fy_range("2099-00") == (date(2099, 4, 1), date(2100, 3, 31))


@pytest.mark.parametrize("bad", ["", "2026", "2026-28", "26-27", "2026-2027", "abcd-ef", "0000-01"])
def test_fy_range_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        fy.fy_range(bad)


def test_fy_of_boundaries() -> None:
    assert fy.fy_of(date(2026, 4, 1)) == "2026-27"
    assert fy.fy_of(date(2027, 3, 31)) == "2026-27"
    assert fy.fy_of(date(2027, 4, 1)) == "2027-28"
    assert fy.fy_of(date(2026, 1, 15)) == "2025-26"
    assert fy.fy_of(date(1999, 12, 31)) == "1999-00"


def test_fy_roundtrip() -> None:
    d = date(2025, 11, 5)
    start, end = fy.fy_range(fy.fy_of(d))
    assert start <= d <= end


def test_current_fy() -> None:
    assert fy.current_fy(date(2026, 3, 31)) == "2025-26"
    assert fy.current_fy(date(2026, 4, 1)) == "2026-27"
    assert fy.current_fy() == fy.fy_of(date.today())


def test_list_fys() -> None:
    today = date(2026, 6, 1)
    assert fy.list_fys(None, today) == ["2026-27"]
    got = fy.list_fys([date(2024, 5, 1), date(2024, 6, 1), date(2025, 6, 1)], today)
    assert got == ["2026-27", "2025-26", "2024-25"]


def test_tables_created(db_session: Session) -> None:
    names = set(inspect(db_session.get_bind()).get_table_names())
    assert {"users", "holdings", "interest", "investments", "trades"} <= names


def _trade(user_id: int, trade_id: str) -> models.Trade:
    return models.Trade(
        user_id=user_id,
        symbol="NIFTY2640722000CE",
        trade_date=date(2026, 4, 7),
        exchange="NSE",
        segment="FO",
        trade_type="buy",
        quantity=Decimal("75"),
        price=Decimal("101.25"),
        trade_id=trade_id,
        order_execution_time=datetime(2026, 4, 7, 9, 30),
        expiry_date=date(2026, 4, 7),
        underlying="NIFTY",
    )


def test_trade_unique_per_user(db_session: Session) -> None:
    u1 = models.User(email="a@x.com", password_hash="h")
    u2 = models.User(email="b@x.com", password_hash="h")
    db_session.add_all([u1, u2])
    db_session.commit()

    db_session.add(_trade(u1.id, "T1"))
    db_session.add(_trade(u2.id, "T1"))  # same trade_id, different user: allowed
    db_session.commit()
    saved = db_session.query(models.Trade).filter_by(user_id=u1.id).one()
    assert saved.price == Decimal("101.2500")

    db_session.add(_trade(u1.id, "T1"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_other_models_persist(db_session: Session) -> None:
    u = models.User(email="c@x.com", password_hash="h")
    db_session.add(u)
    db_session.commit()
    db_session.add_all(
        [
            models.Holding(user_id=u.id, name="G-Sec", kind="gsec", amount=Decimal("1000.50"), as_of_date=date(2026, 4, 1)),
            models.Interest(user_id=u.id, date=date(2026, 5, 1), amount=Decimal("10")),
            models.Investment(user_id=u.id, date=date(2026, 5, 2), amount=Decimal("5000")),
        ]
    )
    db_session.commit()
    assert db_session.query(models.Investment).one().amount == Decimal("5000.00")


def test_schemas_validation() -> None:
    c = schemas.Credentials(email="  A@X.com ", password="longenough")
    assert c.email == "a@x.com"
    with pytest.raises(ValidationError):
        schemas.Credentials(email="nope", password="longenough")
    with pytest.raises(ValidationError):
        schemas.Credentials(email="a@x.com", password="short")
    with pytest.raises(ValidationError):
        schemas.EntryIn(date=date(2026, 4, 1), amount=Decimal("-1"))
    with pytest.raises(ValidationError):
        schemas.HoldingIn(name="x", kind="bogus", amount=Decimal("1"), as_of_date=date(2026, 4, 1))
    assert schemas.EntryIn(date=date(2026, 4, 1), amount=Decimal("1.50")).note == ""
