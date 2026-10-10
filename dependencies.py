"""Authentication dependencies — JWT in HTTP-only cookie OR Authorization header."""
from __future__ import annotations

import datetime as dt
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.dal import AccountDAL
from app.db.models import Account
from app.db.session import get_db

_settings = get_settings()
_bearer = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(account_id: int) -> str:
    now = dt.datetime.utcnow()
    payload = {
        "sub": str(account_id),
        "iat": now,
        "exp": now + dt.timedelta(hours=_settings.TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _settings.SECRET_KEY, algorithm="HS256")


def _decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, _settings.SECRET_KEY, algorithms=["HS256"])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def _extract_token(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """Try Authorization header first, then HTTP-only cookie."""
    if creds and creds.credentials:
        return creds.credentials
    cookie_val = request.cookies.get(_settings.COOKIE_NAME)
    if cookie_val:
        return cookie_val
    return None


def get_current_account(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Account:
    """FastAPI dependency — every protected route depends on this."""
    token = _extract_token(request, creds)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "NO_TOKEN", "message": "Authentication required."},
        )

    account_id = _decode_token(token)
    if account_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired."},
        )

    account = AccountDAL(db).get_by_id(account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ACCOUNT_GONE", "message": "Account no longer exists."},
        )

    return account
