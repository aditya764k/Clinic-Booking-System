"""
Authentication endpoints.

All endpoints live under the /auth prefix (set in main.py).

Design decisions:
- Auto-login on register: POST /register issues cookies immediately so the
  frontend has an authenticated session without a second round-trip.
- Tokens are NEVER returned in the JSON body — HttpOnly cookies only.
- Google SSO creates 'patient' accounts only; doctor/receptionist accounts
  must be provisioned via email+password by an admin/seed process.
"""
import logging
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    TokenExpiredError,
    InvalidTokenError,
)
from app.models.identity import DoctorProfile, PatientProfile, User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

# ── Google OAuth client setup ─────────────────────────────────────────────────

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


# ── Cookie helpers ────────────────────────────────────────────────────────────

def _set_auth_cookies(response: Response, user: User) -> None:
    """Attach access + refresh token cookies to *response*."""
    access_token = create_access_token(user.id, _role_str(user))
    refresh_token = create_refresh_token(user.id)

    cookie_kwargs: dict[str, Any] = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": "strict",
    }

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 24 * 60 * 60,
        **cookie_kwargs,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Expire both auth cookies (effectively logging the user out)."""
    response.delete_cookie("access_token", httponly=True, samesite="strict")
    response.delete_cookie("refresh_token", httponly=True, samesite="strict")


def _role_str(user: User) -> str:
    """Return the role as a plain string regardless of whether it's an Enum or str."""
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def _user_out(user: User) -> UserOut:
    profile_id = None
    role = _role_str(user)
    if role == "doctor" and user.doctor_profile:
        profile_id = user.doctor_profile.id
    elif role == "patient" and user.patient_profile:
        profile_id = user.patient_profile.id

    return UserOut(
        id=user.id,
        email=user.email,
        role=role,
        created_at=user.created_at,
        profile_id=profile_id,
    )


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> Any:
    """Register a new user and auto-login (issues cookies).

    Creates the matching PatientProfile or DoctorProfile in the same
    transaction; rolls back both if either insert fails.
    """
    # Check email uniqueness before attempting the insert
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    try:
        role_enum = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid role")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=role_enum,
    )
    db.add(user)
    db.flush()  # get user.id before creating profile

    # Create linked profile in the same transaction
    if role_enum == UserRole.patient:
        db.add(PatientProfile(user_id=user.id, full_name=body.full_name))
    elif role_enum == UserRole.doctor:
        db.add(DoctorProfile(user_id=user.id, full_name=body.full_name))
    # receptionist → no profile table

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed due to a conflict — email may already be taken",
        )

    db.refresh(user)
    _set_auth_cookies(response, user)
    return _user_out(user)


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=UserOut)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> Any:
    """Authenticate with email + password and issue HttpOnly cookies."""
    user = db.query(User).filter(User.email == body.email).first()

    # Use constant-time passlib verify — do not short-circuit on "user not found"
    # to avoid timing-based user enumeration.
    # This is a pre-computed bcrypt hash of "__dummy__" so the verify() call
    # always runs even when the user doesn't exist, preventing timing attacks.
    _DUMMY_HASH = "$2b$12$K.PbqaBNNsCIblGKAkI2JONvD6HKHJTbqlrRGIPsb4kzX3xhv/Gqq"
    password_ok = verify_password(body.password, user.hashed_password if user else _DUMMY_HASH)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    _set_auth_cookies(response, user)
    return _user_out(user)


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    """Issue a new access token using the refresh token cookie.

    The access token does not need to be valid for this to succeed —
    that's the entire purpose of the refresh flow.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token cookie",
        )

    try:
        payload = decode_token(refresh_token)
    except TokenExpiredError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type for refresh")

    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token(user.id, _role_str(user))
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
    )


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Clear both auth cookies, effectively logging the user out.

    Does not require authentication — clearing cookies is always safe.
    """
    _clear_auth_cookies(response)


# ── Whoami ────────────────────────────────────────────────────────────────────

@router.get("/whoami", response_model=UserOut)
def whoami(current_user: User = Depends(get_current_user)) -> Any:
    """Return the identity of the currently authenticated user.

    Identity is derived entirely from the access_token cookie + DB lookup.
    No query params or headers are used for identity.
    """
    return _user_out(current_user)


# ── Google SSO ────────────────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login(request: Request) -> RedirectResponse:
    """Redirect the browser to Google's OAuth consent screen."""
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle the OAuth authorization code callback from Google.

    Logic:
    1. Exchange code for token, verify ID token.
    2. If user with google_sub exists → log in.
    3. Elif user with same email exists → link google_sub, log in.
    4. Else → create patient + PatientProfile, log in.
    Redirects to FRONTEND_ORIGIN with cookies set (browser flow).
    """
    try:
        token_data = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        logger.warning("Google OAuth token exchange failed: %s", exc)
        raise HTTPException(status_code=400, detail="OAuth token exchange failed")

    user_info: dict = token_data.get("userinfo") or {}
    google_sub: str = user_info.get("sub", "")
    email: str = user_info.get("email", "")
    name: str = user_info.get("name", "") or email.split("@")[0]

    if not google_sub or not email:
        raise HTTPException(status_code=400, detail="Could not retrieve user info from Google")

    # 1. Lookup by google_sub
    user = db.query(User).filter(User.google_sub == google_sub).first()

    if user is None:
        # 2. Lookup by email (link accounts)
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_sub = google_sub
            db.commit()
            db.refresh(user)
        else:
            # 3. New user — create as patient
            user = User(
                email=email,
                google_sub=google_sub,
                role=UserRole.patient,
            )
            db.add(user)
            db.flush()
            db.add(PatientProfile(user_id=user.id, full_name=name))
            db.commit()
            db.refresh(user)

    # Issue cookies and redirect to frontend
    redirect = RedirectResponse(url=settings.FRONTEND_ORIGIN)
    _set_auth_cookies(redirect, user)
    return redirect
