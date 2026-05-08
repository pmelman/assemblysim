"""
Settings API Router

REST API endpoints for managing persistent application defaults.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.models import AppSettings
from app.models.schemas import (
    AppSettingsResponse,
    AppSettingsUpdateRequest,
    AvailableModelsResponse,
    ModelOption,
)
from app.api.auth import require_admin
from app.models_catalog import AVAILABLE_MODELS, DEFAULT_CITIZEN_MODEL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create_settings(db: Session) -> AppSettings:
    """Get the singleton settings row, creating it with defaults if it doesn't exist."""
    settings = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if not settings:
        settings = AppSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=AppSettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Get application settings (creates default row if none exists)."""
    settings = _get_or_create_settings(db)
    return settings


@router.put("", response_model=AppSettingsResponse)
def update_settings(
    request: AppSettingsUpdateRequest,
    admin: None = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Partial update of application settings (admin only)."""
    settings = _get_or_create_settings(db)

    UPDATABLE_FIELDS = {
        "default_num_citizens", "default_num_groups", "default_num_rounds",
        "default_sampling_strategy", "default_round_prompts",
        "default_max_research_calls_per_round", "default_max_research_tokens_per_call",
        "default_citizen_model",
    }

    update_data = request.model_dump(exclude_unset=True)
    # Convert RoundPromptConfig objects to dicts if present
    if "default_round_prompts" in update_data and update_data["default_round_prompts"] is not None:
        update_data["default_round_prompts"] = [
            rp.model_dump() if hasattr(rp, "model_dump") else rp
            for rp in update_data["default_round_prompts"]
        ]

    for field, value in update_data.items():
        if field not in UPDATABLE_FIELDS:
            raise HTTPException(status_code=400, detail=f"Field '{field}' is not updatable")
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    logger.info("Application settings updated")
    return settings


@router.get("/models", response_model=AvailableModelsResponse)
def list_available_models(db: Session = Depends(get_db)):
    """List the curated LLM model options users can pick from."""
    settings = _get_or_create_settings(db)
    return AvailableModelsResponse(
        models=[ModelOption(**m) for m in AVAILABLE_MODELS],
        default_citizen_model=settings.default_citizen_model or DEFAULT_CITIZEN_MODEL,
    )
