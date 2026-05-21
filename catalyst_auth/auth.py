"""Auth utilities — password hashing, JWT creation/verification, API token generation."""
from __future__ import annotations
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY  = os.environ.get("SECRET_KEY", secrets.token_hex(32))
ALGORITHM   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: str | UUID,
    role: str,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub":  str(user_id),
        "role": role,
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# API Tokens (opaque, stored as SHA-256 hash)
# ---------------------------------------------------------------------------

def generate_api_token() -> tuple[str, str]:
    """Return (raw_token, hash). Store only the hash."""
    raw = "cat_" + secrets.token_urlsafe(40)
    h   = hashlib.sha256(raw.encode()).hexdigest()
    return raw, h


def hash_api_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------

def generate_session_token() -> str:
    return secrets.token_urlsafe(48)
