"""Authentication API schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class AccessTokenResponse(BaseModel):
    """Access token response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class UserInfo(BaseModel):
    """User information schema."""

    user_id: str
    username: str
    role: str
    full_name: str | None = None
