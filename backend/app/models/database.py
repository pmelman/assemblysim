"""
Database Configuration Module

Provides SQLAlchemy engine, session management, and database utilities
for the Silicon Citizens' Assembly backend.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.config import get_settings


# Create declarative base for models
Base = declarative_base()


def get_engine():
    """Create and return the SQLAlchemy engine."""
    settings = get_settings()

    # SQLite-specific connection args
    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        connect_args=connect_args
    )
    return engine


# Create engine instance
engine = get_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions in background tasks.

    Usage:
        with get_db_session() as db:
            db.add(item)
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.

    Call this on application startup to ensure tables exist.
    """
    # Import all models to register them with Base
    from app.models import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all tables. Use with caution!

    Primarily for testing and development.
    """
    Base.metadata.drop_all(bind=engine)
