"""Holdings, interest and investments (GET/POST/DELETE, fy-filtered, user-scoped).

Also mounts the summary/fy router, since main.py wires only this module.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Holding, Interest, Investment, User
from app.routers import summary
from app.routers.summary import fy_bounds
from app.schemas import EntryIn, EntryOut, HoldingIn, HoldingOut
from app.security import current_user

router = APIRouter(prefix="/api", tags=["investments"])
router.include_router(summary.router)


# --- holdings ---
@router.get("/holdings", response_model=list[HoldingOut])
def list_holdings(
    fy: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Holding]:
    start, end = fy_bounds(fy)
    stmt = (
        select(Holding)
        .where(Holding.user_id == user.id, Holding.as_of_date.between(start, end))
        .order_by(Holding.as_of_date.desc(), Holding.id.desc())
    )
    return list(db.scalars(stmt))


@router.post("/holdings", response_model=HoldingOut, status_code=status.HTTP_201_CREATED)
def add_holding(
    body: HoldingIn, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> Holding:
    row = Holding(user_id=user.id, **body.model_dump())
    db.add(row)
    db.commit()
    return row


@router.delete("/holdings/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding(
    item_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> Response:
    return _delete(db, Holding, item_id, user)


# --- interest ---
@router.get("/interest", response_model=list[EntryOut])
def list_interest(
    fy: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Interest]:
    start, end = fy_bounds(fy)
    stmt = (
        select(Interest)
        .where(Interest.user_id == user.id, Interest.date.between(start, end))
        .order_by(Interest.date.desc(), Interest.id.desc())
    )
    return list(db.scalars(stmt))


@router.post("/interest", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def add_interest(
    body: EntryIn, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> Interest:
    row = Interest(user_id=user.id, **body.model_dump())
    db.add(row)
    db.commit()
    return row


@router.delete("/interest/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interest(
    item_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> Response:
    return _delete(db, Interest, item_id, user)


# --- investments ---
@router.get("/investments", response_model=list[EntryOut])
def list_investments(
    fy: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Investment]:
    start, end = fy_bounds(fy)
    stmt = (
        select(Investment)
        .where(Investment.user_id == user.id, Investment.date.between(start, end))
        .order_by(Investment.date.desc(), Investment.id.desc())
    )
    return list(db.scalars(stmt))


@router.post("/investments", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def add_investment(
    body: EntryIn, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> Investment:
    row = Investment(user_id=user.id, **body.model_dump())
    db.add(row)
    db.commit()
    return row


@router.delete("/investments/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment(
    item_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> Response:
    return _delete(db, Investment, item_id, user)


def _delete(
    db: Session, model: type[Holding] | type[Interest] | type[Investment], item_id: int, user: User
) -> Response:
    """Delete one row owned by ``user``; 404 if absent or owned by someone else."""
    row = db.scalar(select(model).where(model.id == item_id, model.user_id == user.id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
