"""
Models Package

SQLAlchemy models, Pydantic schemas, and database utilities.
"""

from app.models.database import (
    Base,
    engine,
    SessionLocal,
    get_db,
    get_db_session,
    init_db,
    drop_db
)

from app.models.models import (
    AssemblyStatus,
    Assembly,
    Citizen,
    DeliberationGroup,
    Message,
    BriefingBook,
    Report
)

from app.models.schemas import (
    AssemblyCreateRequest,
    AssemblyResponse,
    AssemblyDetailResponse,
    AssemblyListResponse,
    CitizenResponse,
    CitizenDetailResponse,
    BriefingBookResponse,
    BriefingGenerateRequest,
    MessageResponse,
    GroupResponse,
    ReportResponse,
    WSMessage,
    HealthResponse,
    ErrorResponse
)

__all__ = [
    # Database
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_session",
    "init_db",
    "drop_db",
    # Models
    "AssemblyStatus",
    "Assembly",
    "Citizen",
    "DeliberationGroup",
    "Message",
    "BriefingBook",
    "Report",
    # Schemas
    "AssemblyCreateRequest",
    "AssemblyResponse",
    "AssemblyDetailResponse",
    "AssemblyListResponse",
    "CitizenResponse",
    "CitizenDetailResponse",
    "BriefingBookResponse",
    "BriefingGenerateRequest",
    "MessageResponse",
    "GroupResponse",
    "ReportResponse",
    "WSMessage",
    "HealthResponse",
    "ErrorResponse",
]
