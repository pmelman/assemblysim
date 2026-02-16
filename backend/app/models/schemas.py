"""
Pydantic Schemas for API Request/Response Validation

Defines the data structures for API communication, including
request bodies, response models, and WebSocket messages.
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, EmailStr


# =============================================================================
# AUTH SCHEMAS
# =============================================================================

class RegisterRequest(BaseModel):
    """Request body for user registration."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    username: str = Field(..., min_length=2, max_length=100, description="Display name")
    invite_code: str = Field(..., description="Valid invite code")


class LoginRequest(BaseModel):
    """Request body for user login."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    """Response model for user info."""
    id: int
    email: str
    username: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response model for authentication token."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    """Request body for changing password."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")


class InviteCodeResponse(BaseModel):
    """Response model for an invite code."""
    id: int
    code: str
    created_at: datetime
    used_at: Optional[datetime] = None
    used_by_username: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class RoundPromptConfig(BaseModel):
    """Configuration for a single deliberation round's prompt."""
    theme: str = Field(..., description="Theme for the round, e.g. 'Initial Reactions'")
    prompt: str = Field(..., description="Custom moderator instructions for the round")


class AssemblyCreateRequest(BaseModel):
    """Request body for creating a new assembly."""
    topic: str = Field(..., min_length=5, max_length=500, description="The policy topic for deliberation")
    num_citizens: int = Field(default=40, ge=8, le=100, description="Number of citizens to generate")
    num_groups: int = Field(default=5, ge=1, le=10, description="Number of deliberation groups")
    num_rounds: int = Field(default=3, ge=1, le=10, description="Number of deliberation rounds")
    sampling_strategy: str = Field(default="stratified", description="Sampling strategy: stratified, quota, or random")
    round_prompts: Optional[list[RoundPromptConfig]] = Field(default=None, description="Per-round themes and prompts")
    max_research_calls_per_round: int = Field(default=2, ge=0, le=10, description="Max Perplexity research calls between rounds")
    max_research_tokens_per_call: int = Field(default=2000, ge=500, le=8000, description="Max tokens per research call")
    custom_citizen_ids: Optional[list[int]] = Field(default=None, description="IDs of custom citizen templates to include")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Should the United States implement a Universal Basic Income?",
                "num_citizens": 40,
                "num_groups": 5,
                "num_rounds": 3,
                "sampling_strategy": "stratified",
                "round_prompts": [
                    {"theme": "Initial Reactions", "prompt": "Focus on first impressions and personal connections..."},
                    {"theme": "Trade-offs & Evidence", "prompt": "Push citizens to engage with evidence..."},
                    {"theme": "Synthesis & Recommendations", "prompt": "Guide toward actionable recommendations..."}
                ],
                "max_research_calls_per_round": 2,
                "max_research_tokens_per_call": 2000
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


class RoundResearchResponse(BaseModel):
    """Response model for follow-up research results."""
    id: int
    assembly_id: int
    round_number: int
    queries: list[str]
    results: list[dict[str, Any]]
    summary_markdown: str
    created_at: datetime

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
    round_prompts: Optional[list[dict[str, str]]] = None
    max_research_calls_per_round: int = 2
    max_research_tokens_per_call: int = 2000
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
    round_research: list[RoundResearchResponse] = []

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


# =============================================================================
# SETTINGS SCHEMAS
# =============================================================================

class AppSettingsResponse(BaseModel):
    """Response model for application settings."""
    id: int = 1
    default_num_citizens: int = 40
    default_num_groups: int = 5
    default_num_rounds: int = 3
    default_sampling_strategy: str = "stratified"
    default_round_prompts: Optional[list[dict[str, str]]] = None
    default_max_research_calls_per_round: int = 2
    default_max_research_tokens_per_call: int = 2000
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AppSettingsUpdateRequest(BaseModel):
    """Request body for updating application settings. All fields optional."""
    default_num_citizens: Optional[int] = Field(default=None, ge=8, le=100)
    default_num_groups: Optional[int] = Field(default=None, ge=1, le=10)
    default_num_rounds: Optional[int] = Field(default=None, ge=1, le=10)
    default_sampling_strategy: Optional[str] = None
    default_round_prompts: Optional[list[RoundPromptConfig]] = None
    default_max_research_calls_per_round: Optional[int] = Field(default=None, ge=0, le=10)
    default_max_research_tokens_per_call: Optional[int] = Field(default=None, ge=500, le=8000)


# =============================================================================
# CUSTOM CITIZEN SCHEMAS
# =============================================================================

class CustomCitizenCreateRequest(BaseModel):
    """Request body for creating a custom citizen template."""
    name: str = Field(..., min_length=1, max_length=100, description="Citizen name")
    mode: str = Field(default="traits", description="Creation mode: 'traits' or 'full'")
    background_summary: Optional[str] = Field(default=None, description="Brief background/bio")
    key_values: Optional[list[str]] = Field(default=None, description="Core values")
    demographic_tags: Optional[list[str]] = Field(default=None, description="Demographic tags")
    political_leaning: Optional[str] = Field(default=None, description="Political leaning (e.g. liberal, moderate, conservative)")
    system_prompt: Optional[str] = Field(default=None, description="Full persona system prompt (required for 'full' mode)")


class CustomCitizenUpdateRequest(BaseModel):
    """Request body for updating a custom citizen template. All fields optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    mode: Optional[str] = None
    background_summary: Optional[str] = None
    key_values: Optional[list[str]] = None
    demographic_tags: Optional[list[str]] = None
    political_leaning: Optional[str] = None
    system_prompt: Optional[str] = None


class CustomCitizenTemplateResponse(BaseModel):
    """Response model for a custom citizen template."""
    id: int
    name: str
    mode: str
    background_summary: Optional[str] = None
    key_values: Optional[list[str]] = None
    demographic_tags: Optional[list[str]] = None
    political_leaning: Optional[str] = None
    system_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
