"""Auth endpoints: register, login, me."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import Credentials, Token, UserOut
from app.security import (
    create_access_token,
    current_user,
    hash_password,
    password_too_long,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(body: Credentials, db: Session = Depends(get_db)) -> Token:
    if password_too_long(body.password):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Password must be at most 72 bytes")
    if db.scalar(select(User).where(User.email == body.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    return Token(access_token=create_access_token(user.id))


@router.post("/login", response_model=Token)
def login(body: Credentials, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == body.email))
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user
