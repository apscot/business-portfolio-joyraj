"""Password hashing (bcrypt), JWT issue/verify and the current_user dependency."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72  # bcrypt ignores anything longer (and newer versions raise)
_bearer = HTTPBearer(auto_error=False)
# Verified against when the email is unknown so login timing does not reveal accounts.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


def password_too_long(password: str) -> bool:
    return len(password.encode()) > MAX_PASSWORD_BYTES


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    """Check a password; always performs one bcrypt comparison."""
    if password_too_long(password):
        return False
    try:
        return bcrypt.checkpw(password.encode(), (password_hash or _DUMMY_HASH).encode()) and (
            password_hash is not None
        )
    except ValueError:
        return False


def _secret() -> str:
    secret = get_settings().jwt_secret
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return secret


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=get_settings().jwt_expire_hours),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the bearer token to a User or raise 401."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            creds.credentials, _secret(), algorithms=[ALGORITHM], options={"require": ["exp", "sub"]}
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
