"""FastAPI dependencies for database and authentication."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from loguru import logger
from sqlmodel import Session, select

from jcselect.api.exceptions import AuthenticationError, AuthorizationError
from jcselect.models import User
from jcselect.utils.auth import jwt_manager
from jcselect.utils.db import get_session


def get_db() -> Session:
    """
    Get database session dependency.

    Returns:
        Database session
    """
    with get_session() as session:
        yield session


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        authorization: Authorization header with Bearer token
        db: Database session

    Returns:
        Current user

    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    if not authorization:
        raise AuthenticationError("Authorization header missing")

    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise AuthenticationError("Invalid authentication scheme")
    except ValueError:
        raise AuthenticationError("Invalid authorization header format")

    # Verify token
    token_data = jwt_manager.verify_token(token, "access")
    if not token_data or not token_data.username:
        raise AuthenticationError("Invalid token")

    # Get user from database
    user = db.exec(select(User).where(User.username == token_data.username)).first()
    if not user:
        raise AuthenticationError("User not found")

    # Check if user is soft-deleted
    if user.deleted_at is not None:
        raise AuthenticationError("User account is deactivated")

    logger.debug(f"Authenticated user: {user.username} (role: {user.role})")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Require admin role dependency.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if admin

    Raises:
        AuthorizationError: If user is not admin
    """
    if current_user.role != "admin":
        raise AuthorizationError("Admin role required")

    return current_user


def require_operator_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Require operator or admin role dependency.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if operator or admin

    Raises:
        AuthorizationError: If user is not operator or admin
    """
    if current_user.role not in ["operator", "admin"]:
        raise AuthorizationError("Operator or admin role required")

    return current_user
