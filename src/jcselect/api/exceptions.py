"""Custom exceptions for the sync API."""
from __future__ import annotations

from fastapi import HTTPException, status


class SyncConflictError(HTTPException):
    """Exception raised when sync conflicts occur."""

    def __init__(self, detail: str = "Sync conflict detected") -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class DependencyConflictError(HTTPException):
    """Exception raised when FK dependency validation fails."""

    def __init__(self, missing_dependencies: list[str]) -> None:
        detail = f"Missing dependencies: {', '.join(missing_dependencies)}"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class AuthenticationError(HTTPException):
    """Exception raised for authentication failures."""

    def __init__(self, detail: str = "Authentication failed") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Exception raised for authorization failures."""

    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class InvalidTokenError(HTTPException):
    """Exception raised for invalid tokens."""

    def __init__(self, detail: str = "Invalid token") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )
