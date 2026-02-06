"""
Pydantic Schemas for API Request/Response Validation

Defines the data structures for API communication, including
request bodies, response models, and WebSocket messages.
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class AssemblyCreateRequest(BaseModel):
    """Request body for creating a new assembly."""
    topic: str = Field(..., min_length=5, max_length=500, description="The policy topic for deliberation")
    num_citizens: int = Field(default=40, ge=8, le=100, description="Number of citizens to generate")
    num_groups: int = Field(default=5, ge=1, le=10, description="Number of deliberation groups")
    num_rounds: int = Field(default=3, ge=1, le=10, description="Number of deliberation rounds")
    sampling_strategy: str = Field(default="stratified", description="Sampling strategy: stratified, quota, or random")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Should the United States implement a Universal Basic Income?",
                "num_citizens": 40,
                "num_groups": 5,
                "num_rounds": 3,
                "sampling_strategy": "stratified"
            }
        }


class BriefingGenerateRequest(BaseModel):
    """Request body for generating a briefing book."""
    depth: str = Field(default="standard", description="Depth of research: quick, standard, or detailed")

    class Config:
        json_schema_extra = {
            "example": {
                "depth": "detailed"
            }
        }


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class CitizenResponse(BaseModel):
    """Response model for a citizen."""
    id: int
    name: str
    background_summary: Optional[str] = None
    key_values: Optional[list[str]] = None
    demographic_tags: Optional[list[str]] = None
    group_id: Optional[int] = None
    final_vote: Optional[str] = None
    vote_reasoning: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CitizenDetailResponse(CitizenResponse):
    """Detailed response model for a citizen including system prompt."""
    system_prompt: str
    gss_data: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class BriefingBookResponse(BaseModel):
    """Response model for a briefing book."""
    id: int
    assembly_id: int
    topic_query: str
    content_markdown: str
    sections: Optional[dict[str, Any]] = None
    sources: Optional[list[dict[str, str]]] = None
    generated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response model for a deliberation message."""
    id: int
    assembly_id: int
    group_id: Optional[int] = None
    citizen_id: Optional[int] = None
    citizen_name: Optional[str] = None
    phase: str
    round_number: Optional[int] = None
    role: str
    content: str
    citations: Optional[list[dict[str, Any]]] = None  # Values can be str or None
    fact_check_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GroupResponse(BaseModel):
    """Response model for a deliberation group."""
    id: int
    name: str
    round_summaries: Optional[list[dict[str, Any]]] = None  # List of {round: int, summary: str}
    consensus_summary: Optional[str] = None
    disagreements_summary: Optional[str] = None
    citizen_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    """Response model for the final assembly report."""
    id: int
    assembly_id: int
    executive_summary: Optional[str] = None
    recommendations: Optional[list[dict[str, Any]]] = None
    vote_tally: Optional[dict[str, int]] = None
    minority_report: Optional[str] = None
    key_themes: Optional[list[str]] = None
    generated_at: datetime

    class Config:
        from_attributes = True


class AssemblyResponse(BaseModel):
    """Basic response model for an assembly."""
    id: int
    topic: str
    status: str
    num_citizens: int
    num_groups: int
    num_rounds: int
    sampling_strategy: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssemblyDetailResponse(AssemblyResponse):
    """Detailed response model for an assembly including related data."""
    citizens: list[CitizenResponse] = []
    groups: list[GroupResponse] = []
    briefing_book: Optional[BriefingBookResponse] = None
    report: Optional[ReportResponse] = None

    class Config:
        from_attributes = True


class AssemblyListResponse(BaseModel):
    """Response model for listing assemblies."""
    assemblies: list[AssemblyResponse]
    total: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# WEBSOCKET SCHEMAS
# =============================================================================

class WSMessage(BaseModel):
    """WebSocket message format."""
    type: str = Field(..., description="Message type: status_update, new_message, error, etc.")
    assembly_id: int
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "status_update",
                    "assembly_id": 1,
                    "data": {"status": "generating_citizens", "progress": 5, "total": 40},
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                {
                    "type": "new_message",
                    "assembly_id": 1,
                    "data": {"message_id": 42, "role": "citizen", "content": "I believe..."},
                    "timestamp": "2024-01-15T10:35:00Z"
                }
            ]
        }


# =============================================================================
# UTILITY SCHEMAS
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    database: str = "connected"


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    status_code: int = 500
