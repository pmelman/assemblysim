"""
Assembly Profiles API Router

REST API endpoints for managing saved assembly settings profiles.
A profile is a named bundle of assembly creation settings (prompts, sizes,
preset delegates, etc.) that the user can load when creating new assemblies.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.models import AssemblyProfile, User
from app.models.schemas import (
    AssemblyProfileCreateRequest,
    AssemblyProfileUpdateRequest,
    AssemblyProfileResponse,
)
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assembly-profiles", tags=["assembly-profiles"])


def _check_profile_owner(profile: AssemblyProfile, user: User):
    """Raise 403 if user doesn't own the profile (admin bypasses)."""
    if user.is_admin:
        return
    if profile.user_id is not None and profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this profile")


@router.post("", response_model=AssemblyProfileResponse, status_code=201)
def create_profile(
    request: AssemblyProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new saved assembly settings profile."""
    profile = AssemblyProfile(
        user_id=current_user.id,
        name=request.name,
        config=request.config,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    logger.info(f"Created assembly profile: {profile.name} (id={profile.id})")
    return profile


@router.get("", response_model=list[AssemblyProfileResponse])
def list_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List assembly profiles owned by the current user (admins see all)."""
    query = db.query(AssemblyProfile)
    if not current_user.is_admin:
        query = query.filter(AssemblyProfile.user_id == current_user.id)
    return query.order_by(AssemblyProfile.updated_at.desc()).all()


@router.get("/{profile_id}", response_model=AssemblyProfileResponse)
def get_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single assembly profile."""
    profile = db.query(AssemblyProfile).filter(AssemblyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Assembly profile not found")
    _check_profile_owner(profile, current_user)
    return profile


@router.put("/{profile_id}", response_model=AssemblyProfileResponse)
def update_profile(
    profile_id: int,
    request: AssemblyProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an assembly profile (rename or replace its config)."""
    profile = db.query(AssemblyProfile).filter(AssemblyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Assembly profile not found")
    _check_profile_owner(profile, current_user)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    logger.info(f"Updated assembly profile {profile_id}")
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an assembly profile."""
    profile = db.query(AssemblyProfile).filter(AssemblyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Assembly profile not found")
    _check_profile_owner(profile, current_user)
    db.delete(profile)
    db.commit()

    logger.info(f"Deleted assembly profile {profile_id}")
