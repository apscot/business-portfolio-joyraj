"""Trade CSV upload and paginated list (user-scoped, FY-filtered)."""
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trade, User
from app.routers.summary import fy_bounds
from app.security import current_user
from app.services import trade_import

router = APIRouter(prefix="/api/trades", tags=["trades"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class InvalidRow(BaseModel):
    row: int
    reason: str


class UploadResult(BaseModel):
    inserted: int
    duplicates: int
    invalid: list[InvalidRow]


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


@router.post("/upload", response_model=UploadResult)
async def upload_trades(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, Any]:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 5 MB")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be UTF-8 CSV") from None
    try:
        valid, invalid = trade_import.parse_csv(io.StringIO(text, newline=""))
    except trade_import.HeaderError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
    inserted, duplicates = trade_import.save(db, user.id, valid)
    return {"inserted": inserted, "duplicates": duplicates, "invalid": invalid}


@router.get("", response_model=TradePage)
def list_trades(
    fy: str | None = Query(default=None),
    page: int = Query(default=1, ge=1, le=1_000_000),
    page_size: int = Query(default=15, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, Any]:
    start, end = fy_bounds(fy)
    where = (Trade.user_id == user.id, Trade.trade_date.between(start, end))
    total = db.scalar(select(func.count()).select_from(Trade).where(*where)) or 0
    stmt = (
        select(Trade)
        .where(*where)
        .order_by(Trade.order_execution_time.desc(), Trade.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return {"items": list(db.scalars(stmt)), "total": total, "page": page, "page_size": page_size}
