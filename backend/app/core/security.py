"""
Security utilities: password hashing and JWT operations.

All JWT operations go through this module — no other code should call
jose.jwt directly. decode_token() raises explicit exceptions so callers
(dependencies) can catch and convert to the right HTTP status.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return bcrypt hash of *plain* password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time compare of *plain* against stored *hashed* password.

    Uses passlib's verify — never do a manual ``==`` on hashes.
    Returns False (not an exception) when the hashed value is None/empty
    so that accounts without passwords (e.g., Google-only users) fail
    gracefully.
    """
    if not hashed:
        return False
    return _pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

class TokenExpiredError(Exception):
    """Raised when the JWT has expired."""


class InvalidTokenError(Exception):
    """Raised for any other JWT validation failure (bad sig, malformed, wrong type…)."""


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_access_token(user_id: int, role: str) -> str:
    """Create a short-lived access JWT.

    Payload claims:
    - ``sub``: str(user_id)
    - ``role``: the user's role string
    - ``type``: "access"
    - ``iat``: issued-at (UTC)
    - ``exp``: expiry (UTC, settings.JWT_EXPIRE_MINUTES from now)
    """
    now = _utcnow()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh JWT (minimal payload).

    Payload claims:
    - ``sub``: str(user_id)
    - ``type``: "refresh"
    - ``exp``: expiry (UTC, settings.JWT_REFRESH_EXPIRE_DAYS from now)
    """
    now = _utcnow()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": now + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT.

    Returns the payload dict on success.
    Raises:
    - ``TokenExpiredError`` if the token is past its ``exp`` claim.
    - ``InvalidTokenError`` for any other failure (bad signature, malformed
      header, missing claims, etc.).
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except JWTError as exc:
        raise InvalidTokenError(f"Token is invalid: {exc}") from exc
