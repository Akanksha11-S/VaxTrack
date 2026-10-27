from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User

bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    # bcrypt only reads the first 72 bytes, so cut explicitly rather than rely on library behaviour.
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    """Always performs one bcrypt comparison so unknown emails take as long as wrong passwords."""
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], (hashed or _DUMMY_HASH).encode()) and hashed is not None
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Your session has expired. Sign in again.", headers={"WWW-Authenticate": "Bearer"}
    )
    if creds is None:
        raise unauthorized
    try:
        payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    if user is None:
        raise unauthorized
    return user
