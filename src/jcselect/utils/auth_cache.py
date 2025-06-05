"""Authentication cache system for offline-first login with token caching."""
from __future__ import annotations

import base64
import getpass
import json
import os
import platform
import stat
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger
from pydantic import BaseModel

from jcselect.api.schemas.auth_schemas import UserInfo


class CachedCredentials(BaseModel):
    """Secure credential cache model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    refresh_expires_at: datetime
    user_info: UserInfo
    selected_pen_id: str | None = None
    last_login: datetime


class TokenEncryption:
    """Handle token encryption/decryption."""

    def __init__(self) -> None:
        """Initialize encryption with machine-specific key."""
        self.key = self._get_or_create_key()
        self.fernet = Fernet(self.key)

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key based on machine ID."""
        cache_dir = Path.home() / ".jcselect"
        cache_dir.mkdir(parents=True, exist_ok=True)

        key_file = cache_dir / ".key"

        if key_file.exists():
            return key_file.read_bytes()

        # Generate key from machine-specific data
        machine_id = self._get_machine_id()
        salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))

        # Store key securely
        key_file.write_bytes(key)

        # Set owner read/write only permissions
        if os.name != "nt":  # Unix-like systems
            key_file.chmod(0o600)
        else:  # Windows - set restricted permissions
            os.chmod(key_file, stat.S_IREAD | stat.S_IWRITE)

        return key

    def _get_machine_id(self) -> str:
        """Get a machine-specific identifier."""
        try:
            # Try to get a stable machine identifier
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    if len(lines) > 1:
                        return lines[1].strip()
            else:
                # Unix-like systems
                machine_id_file = Path("/etc/machine-id")
                if machine_id_file.exists():
                    return machine_id_file.read_text().strip()

                # Fallback for macOS
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return result.stdout.strip()

        except Exception as e:
            logger.warning(f"Could not get machine ID: {e}")

        # Fallback to hostname + username
        return f"{platform.node()}-{getpass.getuser()}"

    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()


class AuthCache:
    """Manages persistent authentication cache."""

    def __init__(self) -> None:
        """Initialize auth cache with encryption."""
        self.cache_path = Path.home() / ".jcselect" / "credentials.json"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.encryption = TokenEncryption()

    def save_credentials(self, credentials: CachedCredentials) -> None:
        """Save encrypted credentials to cache file."""
        try:
            # Encrypt sensitive fields before storage
            encrypted_data = self._encrypt_credentials(credentials)

            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(encrypted_data, f, indent=2, default=str)

            logger.info("Credentials cached successfully")

        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise

    def load_credentials(self) -> CachedCredentials | None:
        """Load and decrypt cached credentials."""
        if not self.cache_path.exists():
            return None

        try:
            with open(self.cache_path, encoding="utf-8") as f:
                encrypted_data = json.load(f)

            return self._decrypt_credentials(encrypted_data)

        except Exception as e:
            logger.warning(f"Failed to load cached credentials: {e}")
            return None

    def clear_credentials(self) -> None:
        """Securely clear cached credentials."""
        try:
            if self.cache_path.exists():
                self.cache_path.unlink()
            logger.info("Cached credentials cleared")
        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")

    def is_token_valid(self, credentials: CachedCredentials) -> bool:
        """Check if access token is still valid."""
        return datetime.utcnow() < credentials.expires_at

    def can_refresh_token(self, credentials: CachedCredentials) -> bool:
        """Check if refresh token is still valid."""
        return datetime.utcnow() < credentials.refresh_expires_at

    def _encrypt_credentials(self, credentials: CachedCredentials) -> dict[str, Any]:
        """Encrypt sensitive credential fields."""
        try:
            # Convert to dict for manipulation
            creds_dict = credentials.model_dump()

            # Encrypt sensitive fields
            creds_dict["access_token"] = self.encryption.encrypt(creds_dict["access_token"])
            creds_dict["refresh_token"] = self.encryption.encrypt(creds_dict["refresh_token"])

            # Convert datetime objects to ISO format strings
            creds_dict["expires_at"] = credentials.expires_at.isoformat()
            creds_dict["refresh_expires_at"] = credentials.refresh_expires_at.isoformat()
            creds_dict["last_login"] = credentials.last_login.isoformat()

            return creds_dict

        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise

    def _decrypt_credentials(self, encrypted_data: dict[str, Any]) -> CachedCredentials:
        """Decrypt credential fields and reconstruct CachedCredentials."""
        try:
            # Decrypt sensitive fields
            encrypted_data["access_token"] = self.encryption.decrypt(encrypted_data["access_token"])
            encrypted_data["refresh_token"] = self.encryption.decrypt(encrypted_data["refresh_token"])

            # Convert ISO format strings back to datetime objects
            encrypted_data["expires_at"] = datetime.fromisoformat(encrypted_data["expires_at"])
            encrypted_data["refresh_expires_at"] = datetime.fromisoformat(encrypted_data["refresh_expires_at"])
            encrypted_data["last_login"] = datetime.fromisoformat(encrypted_data["last_login"])

            # Reconstruct UserInfo object
            user_info_data = encrypted_data["user_info"]
            encrypted_data["user_info"] = UserInfo(**user_info_data)

            return CachedCredentials(**encrypted_data)

        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise
