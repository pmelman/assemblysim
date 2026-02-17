"""
FastAPI Application Entry Point

Main application module for the Silicon Citizens' Assembly backend.
Configures the FastAPI app, middleware, and routes.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.database import init_db, get_db
from app.api.assemblies import router as assemblies_router
from app.api.websocket import router as websocket_router
from app.api.settings import router as settings_router
from app.api.custom_citizens import router as custom_citizens_router
from app.api.auth import router as auth_router, get_current_user, hash_password
from app.models.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def seed_admin_user():
    """Create admin user from env vars if no users exist."""
    from app.models.database import SessionLocal
    from app.models.models import User

    settings = get_settings()
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set, skipping admin seed")
        return

    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            admin = User(
                email=settings.ADMIN_EMAIL,
                username="admin",
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            logger.info(f"Admin user created: {settings.ADMIN_EMAIL}")
        else:
            logger.info(f"Users already exist ({user_count}), skipping admin seed")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed admin user: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Silicon Citizens' Assembly API...")
    settings = get_settings()
    logger.info(f"App: {settings.APP_NAME} v{settings.APP_VERSION}")

    # Validate SECRET_KEY is configured
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 16:
        raise RuntimeError(
            "SECRET_KEY must be set in .env and be at least 16 characters. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Seed admin user if needed
    seed_admin_user()

    yield

    # Shutdown
    logger.info("Shutting down Silicon Citizens' Assembly API...")


# Create FastAPI application
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    description="A deliberative democracy simulation using AI agents based on real demographic data",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH CHECK ENDPOINTS (unauthenticated)
# =============================================================================

@app.get("/", tags=["health"])
def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check():
    """Health check endpoint."""
    from app.models.database import engine
    from sqlalchemy import text

    # Check database connection
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.APP_VERSION,
        database=db_status
    )


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

# Auth router (unauthenticated — handles its own auth)
app.include_router(auth_router)

# Protected routers — require valid JWT for all endpoints
app.include_router(assemblies_router, dependencies=[Depends(get_current_user)])
app.include_router(settings_router, dependencies=[Depends(get_current_user)])
app.include_router(custom_citizens_router, dependencies=[Depends(get_current_user)])

# WebSocket router (authenticates via token query param)
app.include_router(websocket_router)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# =============================================================================
# DEVELOPMENT ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
