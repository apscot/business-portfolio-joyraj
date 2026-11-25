"""Pydantic schemas: validation at the HTTP boundary."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
Amount = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth ---
class Credentials(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: int
    email: str


# --- holdings ---
class HoldingIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["gsec", "mutual_fund", "other"]
    amount: Amount
    as_of_date: date


class HoldingOut(ORMModel):
    id: int
    name: str
    kind: str
    amount: Decimal
    as_of_date: date


# --- interest / investments ---
class EntryIn(BaseModel):
    date: date
    amount: Amount
    note: Note = ""


class EntryOut(ORMModel):
    id: int
    date: date
    amount: Decimal
    note: str


# --- trades ---
class TradeOut(ORMModel):
    id: int
    symbol: str
    isin: str
    trade_date: date
    exchange: str
    segment: str
    series: str
    trade_type: str
    auction: bool
    quantity: Decimal
    price: Decimal
    trade_id: str
    order_id: str
    order_execution_time: datetime
    expiry_date: date | None
    underlying: str


class TradePage(BaseModel):
    items: list[TradeOut]
    total: int
    page: int
    page_size: int


class InvalidRow(BaseModel):
    row: int
    reason: str


class UploadResult(BaseModel):
    inserted: int
    duplicates: int
    invalid: list[InvalidRow]
