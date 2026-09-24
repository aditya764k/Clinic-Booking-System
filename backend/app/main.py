"""
FastAPI application entry point.

CORS is configured with allow_credentials=True and a specific origin
(not "*") so HttpOnly cookies are forwarded on cross-origin requests
from the React dev server.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.scheduling import router as scheduling_router

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


@app.get("/health")
def health_check() -> dict:
    return {"status": "healthy"}