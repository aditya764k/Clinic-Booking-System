"""
FastAPI application entry point.

CORS is configured with allow_credentials=True and a specific origin
(not "*") so HttpOnly cookies are forwarded on cross-origin requests
from the React dev server.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.exceptions import IllegalTransitionError
from app.api.auth import router as auth_router
from app.api.scheduling import router as scheduling_router
from app.api.appointment_state import router as appointment_state_router

app = FastAPI(title="Clinic Appointment API")

# SessionMiddleware is required by authlib's starlette OAuth client
# to store the OAuth state/nonce between the redirect and callback.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET_KEY,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,  # Required for cross-origin cookie forwarding
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(scheduling_router)
app.include_router(appointment_state_router)


@app.exception_handler(IllegalTransitionError)
async def illegal_transition_handler(request: Request, exc: IllegalTransitionError):
    """Convert IllegalTransitionError → HTTP 409 with structured JSON body."""
    cur = (
        exc.current_status.value
        if hasattr(exc.current_status, "value")
        else str(exc.current_status)
    )
    att = (
        exc.attempted_status.value
        if hasattr(exc.attempted_status, "value")
        else str(exc.attempted_status)
    )
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
            "current_status": cur,
            "attempted_status": att,
        },
    )


@app.get("/health")
def health_check() -> dict:
    return {"status": "healthy"}