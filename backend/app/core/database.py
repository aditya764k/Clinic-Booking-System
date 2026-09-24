"""
Database engine, session factory, and declarative Base.
All models import Base from here.

DATABASE_URL resolution order:
1. Already set in environment (Docker injects it via env_file) → use as-is.
2. Not set → try loading from .env at various candidate locations
   (works when running scripts locally outside Docker).
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

if "DATABASE_URL" not in os.environ:
    # Try candidate .env paths so local `python scripts/...` runs also work
    _this_file = Path(__file__).resolve()
    for _candidate in [
        _this_file.parents[3] / ".env",   # clinic-app/.env  (running from host)
        _this_file.parents[2] / ".env",   # backend/.env     (fallback)
        Path(".env"),                      # cwd fallback
    ]:
        if _candidate.exists():
            load_dotenv(dotenv_path=_candidate)
            break

DATABASE_URL: str = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency – yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

