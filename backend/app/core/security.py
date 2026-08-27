"""
Password hashing and JWT token utilities.

Kept separate from auth business logic (services/auth_service.py) so these
pure functions can be unit-tested without a database or HTTP layer.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

# Monkeypatch passlib + bcrypt 4.x compatibility
if not hasattr(bcrypt, "__about__"):
    class _About:
        __version__ = getattr(bcrypt, "__version__", "4.0.0")
    bcrypt.__about__ = _About()

try:
    from passlib.handlers.bcrypt import _BcryptBackend
    orig_calc_checksum = _BcryptBackend._calc_checksum
    def patched_calc_checksum(self, secret):
        if isinstance(secret, str):
            secret = secret.encode("utf-8")
        if isinstance(secret, bytes) and len(secret) > 72:
            secret = secret[:72]
        return orig_calc_checksum(self, secret)
    _BcryptBackend._calc_checksum = patched_calc_checksum
except Exception:
    pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    """
    Hash plain text password safely using native bcrypt with passlib fallback.
    """
    try:
        pwd_bytes = plain_password.encode("utf-8")
        if len(pwd_bytes) > 72:
            pwd_bytes = pwd_bytes[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")
    except Exception as e:
        logger.warning(f"Native bcrypt hashing failed, falling back to passlib: {e}")
        return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain text password against hash safely.
    Guaranteed never to throw an unhandled exception.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        pwd_bytes = plain_password.encode("utf-8")
        if len(pwd_bytes) > 72:
            pwd_bytes = pwd_bytes[:72]
        hash_bytes = hashed_password.encode("utf-8")

        # Check native bcrypt first
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$"):
            return bcrypt.checkpw(pwd_bytes, hash_bytes)

        # Fallback to passlib context
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as exc:
        logger.warning(f"Error verifying password with native bcrypt, trying passlib fallback: {exc}")
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e2:
            logger.error(f"Passlib fallback password verification failed: {e2}")
            return False


def create_token(subject: str, role: str, token_type: TokenType, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Create a signed JWT.
    """
    now = datetime.now(timezone.utc)
    if token_type == "access":
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
