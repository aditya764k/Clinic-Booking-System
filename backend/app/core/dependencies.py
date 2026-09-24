"""
FastAPI dependency functions for authentication and role-based access control.

Rules:
- ``get_current_user`` is the SINGLE source of truth for identity.
  No other code should call ``decode_token`` directly.
- ``require_role(*roles)`` is a dependency factory used on protected routes.
"""
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token, TokenExpiredError, InvalidTokenError
from app.models.identity import User


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the access token from the ``access_token`` cookie.

    Returns the authenticated ``User`` ORM object.
    Raises ``HTTP 401`` on missing cookie, expired token, or invalid signature.
    """
    token: str | None = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — missing access token cookie",
        )

    try:
        payload = decode_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    # Verify this is an access token, not a refresh token sneaked in
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed subject claim",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def require_role(*allowed_roles: str) -> Callable:
    """Dependency factory for role-based access control.

    Usage examples::

        @router.get("/doctor-only")
        def endpoint(user: User = Depends(require_role("doctor"))):
            ...

        @router.get("/staff")
        def endpoint(user: User = Depends(require_role("doctor", "receptionist"))):
            ...

    Raises ``HTTP 403`` when the authenticated user's role is not in *allowed_roles*.
    """

    def _check_role(current_user: User = Depends(get_current_user)) -> User:
        role_value = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else str(current_user.role)
        )
        if role_value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check_role
