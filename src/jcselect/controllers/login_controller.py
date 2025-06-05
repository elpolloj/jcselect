"""Login controller for authentication, token management, and session persistence."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import bcrypt
import httpx
from loguru import logger
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from sqlmodel import select

from jcselect.api.schemas.auth_schemas import LoginRequest, UserInfo
from jcselect.models.user import User
from jcselect.utils.auth import JWTManager, jwt_manager
from jcselect.utils.auth_cache import AuthCache, CachedCredentials
from jcselect.utils.db import get_session
from jcselect.utils.settings import sync_settings


class APIClient:
    """Simple HTTP client for API authentication requests."""

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize API client with base URL."""
        self.base_url = base_url or str(sync_settings.sync_api_url).rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def post(self, endpoint: str, data: dict[str, Any]) -> httpx.Response:
        """Make a POST request to the API."""
        url = f"{self.base_url}/api/v1{endpoint}"
        return self.client.post(url, json=data)

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()


class LoginController(QObject):
    """Handles authentication, token management, and session persistence."""

    # Signals
    loginSuccessful = Signal(dict)  # user_info
    loginFailed = Signal(str)  # error_message
    tokenRefreshed = Signal()
    logoutCompleted = Signal()
    penSelectionRequired = Signal()
    penSelectionCompleted = Signal(str)  # pen_id
    connectionStatusChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize login controller with dependencies."""
        super().__init__(parent)
        self.auth_cache = AuthCache()
        self.api_client = APIClient()
        self.jwt_manager: JWTManager = jwt_manager
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_token_background)
        self._current_user: dict[str, Any] | None = None
        self._selected_pen: str | None = None
        self._is_online = False
        self._is_logged_in = False
        self._pen_selection_requested = False  # Flag to ensure pen selection is requested only once

    # Properties
    def _get_is_logged_in(self) -> bool:
        """Get login status."""
        return self._is_logged_in

    def _set_is_logged_in(self, value: bool) -> None:
        """Set login status."""
        self._is_logged_in = value

    isLoggedIn = Property(bool, _get_is_logged_in, _set_is_logged_in, notify=loginSuccessful)  # type: ignore[call-arg,arg-type]

    def _get_current_user(self) -> dict[str, Any] | None:
        """Get current user info."""
        return self._current_user

    def _set_current_user(self, value: dict[str, Any] | None) -> None:
        """Set current user info."""
        self._current_user = value

    currentUser = Property("QVariant", _get_current_user, _set_current_user, notify=loginSuccessful)  # type: ignore[call-arg,arg-type]

    def _get_is_online(self) -> bool:
        """Get online status."""
        return self._is_online

    def _set_is_online(self, value: bool) -> None:
        """Set online status."""
        self._is_online = value

    isOnline = Property(bool, _get_is_online, _set_is_online, notify=connectionStatusChanged)  # type: ignore[call-arg,arg-type]

    def _get_selected_pen(self) -> str | None:
        """Get selected pen ID."""
        return self._selected_pen

    def _set_selected_pen(self, value: str | None) -> None:
        """Set selected pen ID."""
        self._selected_pen = value

    selectedPen = Property("QVariant", _get_selected_pen, _set_selected_pen, notify=penSelectionCompleted)  # type: ignore[call-arg,arg-type]

    @Slot(str, str, bool)
    def authenticate(self, username: str, password: str, remember_me: bool = True) -> None:
        """Authenticate user with online/offline fallback."""
        logger.info(f"=== Authentication started for user: {username} ===")
        logger.info(f"Remember me: {remember_me}")
        
        try:
            # Try online authentication first
            logger.info("Attempting online login...")
            if self._attempt_online_login(username, password, remember_me):
                logger.info("Online login successful")
                return

            # Try direct database authentication (for local development)
            logger.info("Attempting database login...")
            if self._attempt_database_login(username, password, remember_me):
                logger.info("Database login successful")
                return

            # Fallback to offline authentication
            logger.info("Attempting offline login...")
            if self._attempt_offline_login(username, password):
                logger.info("Offline login successful")
                return

            logger.warning("All authentication methods failed")
            self.loginFailed.emit("Invalid credentials")

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.loginFailed.emit(f"Authentication error: {str(e)}")

    @Slot(result=bool)
    def autoLoginIfPossible(self) -> bool:
        """Attempt automatic login with cached credentials."""
        try:
            cached_creds = self.auth_cache.load_credentials()

            if not cached_creds:
                logger.debug("No cached credentials found")
                return False

            # Check if we can refresh the token
            if self.auth_cache.can_refresh_token(cached_creds):
                if self.auth_cache.is_token_valid(cached_creds):
                    # Token still valid, use directly
                    self._handle_cached_login(cached_creds)
                    return True
                else:
                    # Try to refresh token
                    if self._refresh_access_token(cached_creds):
                        return True

            # Clear invalid credentials
            self.auth_cache.clear_credentials()
            logger.debug("Cached credentials expired and cannot be refreshed")
            return False

        except Exception as e:
            logger.error(f"Auto-login failed: {e}")
            return False

    @Slot(str)
    def selectPen(self, pen_id: str) -> None:
        """Select and persist pen choice."""
        try:
            cached_creds = self.auth_cache.load_credentials()
            if cached_creds:
                cached_creds.selected_pen_id = pen_id
                self.auth_cache.save_credentials(cached_creds)

            self._selected_pen = pen_id
            self.penSelectionCompleted.emit(pen_id)

            # Now emit login successful
            if self._current_user:
                self.loginSuccessful.emit(self._current_user)

        except Exception as e:
            logger.error(f"Pen selection failed: {e}")
            self.loginFailed.emit(f"Pen selection failed: {str(e)}")

    @Slot()
    def logout(self) -> None:
        """Logout user and clear all cached data."""
        try:
            self.refresh_timer.stop()
            self.auth_cache.clear_credentials()
            self._current_user = None
            self._selected_pen = None
            self._is_logged_in = False
            self._pen_selection_requested = False  # Reset pen selection flag
            self.logoutCompleted.emit()
            logger.info("User logged out successfully")

        except Exception as e:
            logger.error(f"Logout failed: {e}")

    def _attempt_online_login(self, username: str, password: str, remember_me: bool) -> bool:
        """Attempt online authentication via API."""
        try:
            login_request = LoginRequest(username=username, password=password)
            response = self.api_client.post("/auth/login", login_request.model_dump())

            if response.status_code == 200:
                token_data = response.json()
                self._handle_successful_login(token_data, remember_me)
                self._is_online = True
                self.connectionStatusChanged.emit()
                return True
            else:
                logger.warning(f"Online login failed with status {response.status_code}")

        except Exception as e:
            logger.warning(f"Online login failed: {e}")

        self._is_online = False
        self.connectionStatusChanged.emit()
        return False

    def _attempt_database_login(self, username: str, password: str, remember_me: bool) -> bool:
        """Attempt direct database authentication for local development."""
        logger.info(f"Database login attempt for username: {username}")
        
        try:
            with get_session() as session:
                # Find user in database
                logger.debug(f"Searching for user: {username}")
                user = session.exec(
                    select(User).where(
                        User.username == username,
                        User.is_active == True,
                        User.deleted_at.is_(None)
                    )
                ).first()
                
                if not user:
                    logger.warning(f"User not found in database: {username}")
                    return False
                
                logger.debug(f"User found: {user.username}, role: {user.role}")
                
                # Verify password
                if not user.password_hash:
                    logger.warning(f"User {username} has no password hash")
                    return False
                
                # Check password with bcrypt
                logger.debug("Verifying password...")
                password_correct = bcrypt.checkpw(
                    password.encode('utf-8'), 
                    user.password_hash.encode('utf-8')
                )
                
                if not password_correct:
                    logger.warning(f"Password verification failed for user: {username}")
                    return False
                
                logger.info(f"Password verified successfully for user: {username}")
                
                # Create mock token response for local development
                user_info_data = {
                    "user_id": str(user.id),
                    "username": user.username,
                    "role": user.role,
                    "full_name": user.full_name
                }
                
                # Mock token data
                token_data = {
                    "access_token": "local_dev_token",
                    "refresh_token": "local_dev_refresh_token",
                    "token_type": "bearer",
                    "expires_in": 3600,  # 1 hour
                    "user_info": user_info_data
                }
                
                logger.info("Handling successful database login...")
                self._handle_successful_login(token_data, remember_me)
                self._is_online = False  # Mark as offline since this is local DB
                self.connectionStatusChanged.emit()
                
                return True
                
        except Exception as e:
            logger.error(f"Database login failed with error: {e}")
            return False

    def _attempt_offline_login(self, username: str, password: str) -> bool:
        """Attempt offline login with cached credentials."""
        try:
            cached_creds = self.auth_cache.load_credentials()

            if not cached_creds:
                logger.debug("No cached credentials for offline login")
                return False

            # Verify username matches cached user
            if cached_creds.user_info.username != username:
                logger.debug("Username mismatch for offline login")
                return False

            # For offline mode, we rely on the cached token being valid
            # In production, you might want to cache password hash for verification
            if self.auth_cache.can_refresh_token(cached_creds):
                self._handle_cached_login(cached_creds)
                logger.info("Offline login successful")
                return True

            logger.debug("Cached credentials cannot be used for offline login")
            return False

        except Exception as e:
            logger.error(f"Offline login failed: {e}")
            return False

    def _handle_successful_login(self, token_data: dict[str, Any], remember_me: bool) -> None:
        """Process successful login response."""
        try:
            # Extract user info from token response
            user_info_data = token_data.get("user_info", {})
            if not user_info_data:
                # If user_info not in response, try to decode from token
                token_payload = self.jwt_manager.verify_token(token_data["access_token"])
                if token_payload:
                    user_info_data = {
                        "user_id": token_payload.user_id,
                        "username": token_payload.username,
                        "role": token_payload.role,
                        "full_name": token_payload.username  # Fallback
                    }

            user_info = UserInfo(**user_info_data)

            # Calculate expiry times
            expires_in = token_data.get("expires_in", 15 * 60)  # Default 15 minutes
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            refresh_expires_at = datetime.utcnow() + timedelta(hours=12)

            # Create cached credentials
            credentials = CachedCredentials(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_type=token_data.get("token_type", "bearer"),
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at,
                user_info=user_info,
                last_login=datetime.utcnow()
            )

            if remember_me:
                self.auth_cache.save_credentials(credentials)

            self._current_user = user_info_data
            self._is_logged_in = True
            self._start_token_refresh_timer(credentials)

            # Admin users don't need pen selection - they have access to all data
            if user_info_data.get("role") == "admin":
                logger.info("Admin user login - bypassing pen selection")
                self._selected_pen = None  # Admin doesn't have a specific pen
                self.loginSuccessful.emit(user_info_data)
            # For non-admin users, check if pen selection is needed
            elif not credentials.selected_pen_id and not self._pen_selection_requested:
                self._pen_selection_requested = True
                logger.info("Operator user login - requesting pen selection")
                self.penSelectionRequired.emit()
            else:
                self._selected_pen = credentials.selected_pen_id
                self.loginSuccessful.emit(user_info_data)

        except Exception as e:
            logger.error(f"Failed to handle successful login: {e}")
            self.loginFailed.emit(f"Login processing failed: {str(e)}")

    def _handle_cached_login(self, credentials: CachedCredentials) -> None:
        """Process login with cached credentials."""
        try:
            self._current_user = credentials.user_info.model_dump()
            self._is_logged_in = True
            self._start_token_refresh_timer(credentials)

            # Admin users don't need pen selection - they have access to all data
            if self._current_user.get("role") == "admin":
                logger.info("Admin user cached login - bypassing pen selection")
                self._selected_pen = None  # Admin doesn't have a specific pen
                self.loginSuccessful.emit(self._current_user)
            # For non-admin users, check if pen selection is needed
            elif not credentials.selected_pen_id and not self._pen_selection_requested:
                self._pen_selection_requested = True
                logger.info("Operator user cached login - requesting pen selection")
                self.penSelectionRequired.emit()
            else:
                self._selected_pen = credentials.selected_pen_id
                self.loginSuccessful.emit(self._current_user)

        except Exception as e:
            logger.error(f"Failed to handle cached login: {e}")
            self.loginFailed.emit(f"Cached login failed: {str(e)}")

    def _refresh_access_token(self, credentials: CachedCredentials) -> bool:
        """Refresh access token using refresh token."""
        try:
            response = self.api_client.post("/auth/refresh", {
                "refresh_token": credentials.refresh_token
            })

            if response.status_code == 200:
                token_data = response.json()

                # Update credentials with new access token
                credentials.access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 15 * 60)
                credentials.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                self.auth_cache.save_credentials(credentials)
                self._handle_cached_login(credentials)
                self.tokenRefreshed.emit()
                logger.info("Access token refreshed successfully")
                return True
            else:
                logger.warning(f"Token refresh failed with status {response.status_code}")

        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")

        return False

    def _start_token_refresh_timer(self, credentials: CachedCredentials) -> None:
        """Start timer for automatic token refresh."""
        try:
            # Calculate time until token expires (refresh 5 minutes before expiry)
            time_until_expiry = credentials.expires_at - datetime.utcnow()
            refresh_time = max(time_until_expiry - timedelta(minutes=5), timedelta(minutes=1))

            if refresh_time.total_seconds() > 0:
                self.refresh_timer.start(int(refresh_time.total_seconds() * 1000))  # QTimer uses ms
                logger.debug(f"Token refresh timer set for {refresh_time.total_seconds()} seconds")
            else:
                logger.warning("Token expires too soon, attempting immediate refresh")
                self._refresh_token_background()

        except Exception as e:
            logger.error(f"Failed to start token refresh timer: {e}")

    def _refresh_token_background(self) -> None:
        """Background token refresh triggered by timer."""
        try:
            self.refresh_timer.stop()

            cached_creds = self.auth_cache.load_credentials()
            if not cached_creds:
                logger.warning("No cached credentials for background refresh")
                return

            if self._refresh_access_token(cached_creds):
                logger.debug("Background token refresh successful")
            else:
                logger.warning("Background token refresh failed - user may need to re-login")
                # Don't auto-logout here, let the user continue until they make a request

        except Exception as e:
            logger.error(f"Background token refresh failed: {e}")

    def __del__(self) -> None:
        """Cleanup resources on destruction."""
        try:
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer.stop()
            if hasattr(self, 'api_client'):
                self.api_client.close()
        except Exception:
            pass  # Ignore cleanup errors
