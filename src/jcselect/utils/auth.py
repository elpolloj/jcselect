"""JWT authentication utilities for the sync API."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from jcselect.utils.settings import sync_settings


class TokenData(BaseModel):
    """Token payload data."""

    username: str | None = None
    user_id: str | None = None
    role: str | None = None
    exp: datetime | None = None


class JWTManager:
    """JWT token manager for authentication."""

    def __init__(self) -> None:
        """Initialize JWT manager with settings."""
        self.secret_key = sync_settings.sync_jwt_secret
        self.algorithm = sync_settings.jwt_algorithm
        self.access_token_expire_minutes = sync_settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_hours = sync_settings.jwt_refresh_token_expire_hours
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Hash a password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    def create_access_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Token payload data
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """
        Create a JWT refresh token.

        Args:
            data: Token payload data
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.refresh_token_expire_hours)

        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> TokenData | None:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token to verify
            token_type: Expected token type ("access" or "refresh")

        Returns:
            TokenData if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check token type
            if payload.get("type") != token_type:
                return None

            # Extract token data
            username: str | None = payload.get("sub")
            user_id: str | None = payload.get("user_id")
            role: str | None = payload.get("role")
            exp_timestamp: int | None = payload.get("exp")

            if username is None:
                return None

            exp = datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None

            return TokenData(
                username=username,
                user_id=user_id,
                role=role,
                exp=exp
            )

        except JWTError:
            return None


# Global JWT manager instance
jwt_manager = JWTManager()
