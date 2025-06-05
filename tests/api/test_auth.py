"""Unit tests for authentication API endpoints."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from jcselect.api.main import app
from jcselect.models import User
from jcselect.utils.auth import jwt_manager


@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing."""
    db_url = "sqlite:///:memory:"
    engine = create_engine(
        db_url, 
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    yield engine


@pytest.fixture
def test_session(temp_db):
    """Create a test database session."""
    with Session(temp_db) as session:
        yield session


@pytest.fixture
def test_client(test_session):
    """Create a test client with mocked database dependency."""
    def override_get_db():
        yield test_session
    
    from jcselect.api.dependencies import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_session):
    """Create a test user in the database."""
    password_hash = jwt_manager.get_password_hash("testpassword")
    
    user = User(
        username="testuser",
        password_hash=password_hash,
        role="operator",
        full_name="Test User"
    )
    
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    
    return user


@pytest.fixture
def admin_user(test_session):
    """Create an admin test user in the database."""
    password_hash = jwt_manager.get_password_hash("adminpassword")
    
    user = User(
        username="admin",
        password_hash=password_hash,
        role="admin",
        full_name="Admin User"
    )
    
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    
    return user


def test_login_success(test_client, test_user):
    """Test successful login."""
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    
    # Verify tokens are valid
    access_token_data = jwt_manager.verify_token(data["access_token"], "access")
    assert access_token_data is not None
    assert access_token_data.username == "testuser"
    
    refresh_token_data = jwt_manager.verify_token(data["refresh_token"], "refresh")
    assert refresh_token_data is not None
    assert refresh_token_data.username == "testuser"


def test_login_invalid_username(test_client, test_user):
    """Test login with invalid username."""
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent",
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_login_invalid_password(test_client, test_user):
    """Test login with invalid password."""
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_login_soft_deleted_user(test_client, test_user):
    """Test login with soft-deleted user."""
    from datetime import datetime
    
    # Soft delete the user
    test_user.deleted_at = datetime.utcnow()
    
    # Get session from dependency override
    def get_test_session():
        for override in test_client.app.dependency_overrides.values():
            return next(override())
    
    session = get_test_session()
    session.add(test_user)
    session.commit()
    
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 401
    assert "User account is deactivated" in response.json()["detail"]


def test_refresh_token_success(test_client, test_user):
    """Test successful token refresh."""
    # First login to get tokens
    login_response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    
    assert login_response.status_code == 200
    tokens = login_response.json()
    
    # Use refresh token to get new access token
    refresh_response = test_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": tokens["refresh_token"]
        }
    )
    
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    
    assert "access_token" in refresh_data
    assert refresh_data["token_type"] == "bearer"
    assert "expires_in" in refresh_data
    
    # Verify new access token is valid
    new_token_data = jwt_manager.verify_token(refresh_data["access_token"], "access")
    assert new_token_data is not None
    assert new_token_data.username == "testuser"


def test_refresh_token_invalid(test_client, test_user):
    """Test refresh with invalid token."""
    response = test_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": "invalid_token"
        }
    )
    
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


def test_get_current_user_info(test_client, test_user):
    """Test getting current user information."""
    # First login to get access token
    login_response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # Get user info
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    user_info = response.json()
    
    assert user_info["username"] == "testuser"
    assert user_info["role"] == "operator"
    assert user_info["full_name"] == "Test User"
    assert "user_id" in user_info


def test_get_current_user_info_no_auth(test_client):
    """Test getting user info without authentication."""
    response = test_client.get("/api/v1/auth/me")
    
    assert response.status_code == 401
    assert "Authorization header missing" in response.json()["detail"]


def test_get_current_user_info_invalid_token(test_client):
    """Test getting user info with invalid token."""
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


@pytest.mark.parametrize("invalid_auth_header", [
    "invalid_format",
    "Basic dGVzdDp0ZXN0",  # Basic auth instead of Bearer
    "Bearer",  # Missing token
])
def test_invalid_authorization_headers(test_client, invalid_auth_header):
    """Test various invalid authorization header formats."""
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": invalid_auth_header}
    )
    
    assert response.status_code == 401 