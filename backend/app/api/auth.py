"""
Authentication API endpoints for Silicon Citizens' Assembly.

Handles user registration (with invite codes), login (JWT), and invite code management.
"""

import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.database import get_db
from app.models.models import User, InviteCode
from app.models.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    InviteCodeResponse,
    ChangePasswordRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token extraction
security = HTTPBearer()


# =============================================================================
# HELPERS
# =============================================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: extract and validate the current user from JWT."""
    settings = get_settings()
    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency: require that the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with a valid invite code."""
    # Check invite code
    invite = db.query(InviteCode).filter(
        InviteCode.code == request.invite_code,
        InviteCode.used_by_user_id.is_(None),
    ).first()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used invite code",
        )

    # Check email uniqueness
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check username uniqueness
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create user
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hash_password(request.password),
        is_admin=False,
    )
    db.add(user)
    db.flush()  # Get user.id before updating invite code

    # Mark invite code as used
    invite.used_by_user_id = user.id
    invite.used_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    logger.info(f"New user registered: {user.email} (id={user.id})")

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and issue a JWT."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=UserResponse)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password."""
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = hash_password(request.new_password)
    db.commit()
    db.refresh(current_user)

    logger.info(f"Password changed for user: {current_user.email}")
    return UserResponse.model_validate(current_user)


@router.post("/invite-codes", response_model=InviteCodeResponse)
def create_invite_code(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Generate a new invite code (admin only)."""
    code = secrets.token_urlsafe(16)
    invite = InviteCode(
        code=code,
        created_by_user_id=admin.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    logger.info(f"Invite code created by {admin.email}: {code[:8]}...")
    return InviteCodeResponse(
        id=invite.id,
        code=invite.code,
        created_at=invite.created_at,
        used_at=invite.used_at,
    )


@router.get("/invite-codes", response_model=list[InviteCodeResponse])
def list_invite_codes(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all invite codes (admin only)."""
    invites = db.query(InviteCode).order_by(InviteCode.created_at.desc()).all()
    results = []
    for invite in invites:
        used_by_username = None
        if invite.used_by_user_id:
            used_by = db.query(User).filter(User.id == invite.used_by_user_id).first()
            if used_by:
                used_by_username = used_by.username
        results.append(InviteCodeResponse(
            id=invite.id,
            code=invite.code,
            created_at=invite.created_at,
            used_at=invite.used_at,
            used_by_username=used_by_username,
        ))
    return results
