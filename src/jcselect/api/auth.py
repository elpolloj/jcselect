"""Authentication API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from loguru import logger
from sqlmodel import Session, select

from jcselect.api.dependencies import get_current_user, get_db
from jcselect.api.exceptions import AuthenticationError, InvalidTokenError
from jcselect.api.schemas.auth_schemas import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserInfo,
)
from jcselect.models import User
from jcselect.utils.auth import jwt_manager
from jcselect.utils.settings import sync_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    login_request: LoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return access and refresh tokens.

    Args:
        login_request: Login credentials
        db: Database session

    Returns:
        Token response with access and refresh tokens

    Raises:
        HTTPException: If authentication fails
    """
    # Find user by username
    user = db.exec(select(User).where(User.username == login_request.username)).first()

    if not user:
        logger.warning(f"Login attempt with non-existent username: {login_request.username}")
        raise AuthenticationError("Invalid username or password")

    # Check if user is soft-deleted
    if user.deleted_at is not None:
        logger.warning(f"Login attempt with deactivated account: {login_request.username}")
        raise AuthenticationError("User account is deactivated")

    # Verify password
    if not jwt_manager.verify_password(login_request.password, user.password_hash):
        logger.warning(f"Invalid password for user: {login_request.username}")
        raise AuthenticationError("Invalid username or password")

    # Create token data
    token_data = {
        "sub": user.username,
        "user_id": str(user.id),
        "role": user.role
    }

    # Generate tokens
    access_token = jwt_manager.create_access_token(token_data)
    refresh_token = jwt_manager.create_refresh_token(token_data)

    # Calculate expiration time in seconds
    expires_in = sync_settings.jwt_access_token_expire_minutes * 60

    logger.info(f"User {user.username} logged in successfully")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    refresh_request: RefreshRequest,
    db: Session = Depends(get_db)
) -> AccessTokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        refresh_request: Refresh token request
        db: Database session

    Returns:
        New access token

    Raises:
        HTTPException: If refresh token is invalid
    """
    # Verify refresh token
    token_data = jwt_manager.verify_token(refresh_request.refresh_token, "refresh")

    if not token_data or not token_data.username:
        raise InvalidTokenError("Invalid refresh token")

    # Verify user still exists and is active
    user = db.exec(select(User).where(User.username == token_data.username)).first()

    if not user:
        raise InvalidTokenError("User not found")

    if user.deleted_at is not None:
        raise InvalidTokenError("User account is deactivated")

    # Create new access token
    new_token_data = {
        "sub": user.username,
        "user_id": str(user.id),
        "role": user.role
    }

    access_token = jwt_manager.create_access_token(new_token_data)
    expires_in = sync_settings.jwt_access_token_expire_minutes * 60

    logger.debug(f"Access token refreshed for user: {user.username}")

    return AccessTokenResponse(
        access_token=access_token,
        expires_in=expires_in
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserInfo:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user from dependency

    Returns:
        Current user information
    """
    return UserInfo(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        full_name=current_user.full_name
    )
