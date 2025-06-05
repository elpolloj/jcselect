"""Unit tests for sync push/pull API endpoints."""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from jcselect.api.main import app
from jcselect.models import Party, Pen, TallySession, User, Voter
from jcselect.models.sync_schemas import ChangeOperation
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
def operator_user(test_session):
    """Create an operator user for testing."""
    password_hash = jwt_manager.get_password_hash("testpassword")
    
    user = User(
        username="operator",
        password_hash=password_hash,
        role="operator",
        full_name="Operator User"
    )
    
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    
    return user


@pytest.fixture
def admin_user(test_session):
    """Create an admin user for testing."""
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


@pytest.fixture
def test_pen(test_session):
    """Create a test pen."""
    pen = Pen(
        town_name="Test Town",
        label="Pen 001"
    )
    
    test_session.add(pen)
    test_session.commit()
    test_session.refresh(pen)
    
    return pen


@pytest.fixture
def test_party(test_session):
    """Create a test party."""
    party = Party(
        party_name="Test Party",
        party_code="TP"
    )
    
    test_session.add(party)
    test_session.commit()
    test_session.refresh(party)
    
    return party


@pytest.fixture
def operator_auth_headers(test_client, operator_user):
    """Get authentication headers for operator user."""
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "operator",
            "password": "testpassword"
        }
    )
    
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def admin_auth_headers(test_client, admin_user):
    """Get authentication headers for admin user."""
    response = test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "adminpassword"
        }
    )
    
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_push_voter_change_success(test_client, operator_auth_headers, test_pen):
    """Test successful push of voter change."""
    voter_id = uuid4()
    
    push_request = {
        "changes": [
            {
                "id": str(uuid4()),
                "entity_type": "Voter",
                "entity_id": str(voter_id),
                "operation": "UPDATE",
                "data": {
                    "id": str(voter_id),
                    "pen_id": str(test_pen.id),
                    "voter_number": "12345",
                    "full_name": "Test Voter",
                    "has_voted": True,
                    "updated_at": datetime.utcnow().isoformat()
                },
                "timestamp": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
        ],
        "client_timestamp": datetime.utcnow().isoformat()
    }
    
    response = test_client.post(
        "/api/v1/sync/push",
        json=push_request,
        headers=operator_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["processed_count"] == 1
    assert len(data["failed_changes"]) == 0
    assert len(data["conflicts"]) == 0
    assert "server_timestamp" in data


def test_push_dependency_conflict(test_client, operator_auth_headers):
    """Test push with missing dependency."""
    tally_line_id = uuid4()
    nonexistent_session_id = uuid4()
    nonexistent_party_id = uuid4()
    
    push_request = {
        "changes": [
            {
                "id": str(uuid4()),
                "entity_type": "TallyLine",
                "entity_id": str(tally_line_id),
                "operation": "CREATE",
                "data": {
                    "id": str(tally_line_id),
                    "tally_session_id": str(nonexistent_session_id),
                    "party_id": str(nonexistent_party_id),
                    "vote_count": 10,
                    "created_at": datetime.utcnow().isoformat()
                },
                "timestamp": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
        ],
        "client_timestamp": datetime.utcnow().isoformat()
    }
    
    response = test_client.post(
        "/api/v1/sync/push",
        json=push_request,
        headers=operator_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["processed_count"] == 0
    assert len(data["failed_changes"]) == 1
    assert len(data["conflicts"]) == 0


def test_push_permission_denied(test_client, operator_auth_headers):
    """Test push with insufficient permissions."""
    user_id = uuid4()
    
    push_request = {
        "changes": [
            {
                "id": str(uuid4()),
                "entity_type": "User",  # Operators can't modify users
                "entity_id": str(user_id),
                "operation": "CREATE",
                "data": {
                    "id": str(user_id),
                    "username": "newuser",
                    "role": "operator",
                    "created_at": datetime.utcnow().isoformat()
                },
                "timestamp": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
        ],
        "client_timestamp": datetime.utcnow().isoformat()
    }
    
    response = test_client.post(
        "/api/v1/sync/push",
        json=push_request,
        headers=operator_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["processed_count"] == 0
    assert len(data["failed_changes"]) == 1
    assert len(data["conflicts"]) == 0


def test_push_conflict_resolution(test_client, operator_auth_headers, test_pen):
    """Test push with timestamp conflict."""
    # First create a voter in the database
    voter_id = uuid4()
    voter = Voter(
        id=voter_id,
        pen_id=test_pen.id,
        voter_number="12345",
        full_name="Existing Voter",
        has_voted=False,
        updated_at=datetime.utcnow()  # Server version is newer
    )
    
    # Get session from dependency override
    def get_test_session():
        for override in test_client.app.dependency_overrides.values():
            return next(override())
    
    session = get_test_session()
    session.add(voter)
    session.commit()
    
    # Try to push an older version
    old_timestamp = datetime.utcnow() - timedelta(hours=1)
    
    push_request = {
        "changes": [
            {
                "id": str(uuid4()),
                "entity_type": "Voter",
                "entity_id": str(voter_id),
                "operation": "UPDATE",
                "data": {
                    "id": str(voter_id),
                    "pen_id": str(test_pen.id),
                    "voter_number": "12345",
                    "full_name": "Client Version",
                    "has_voted": True,
                    "updated_at": old_timestamp.isoformat()
                },
                "timestamp": old_timestamp.isoformat(),
                "retry_count": 0
            }
        ],
        "client_timestamp": datetime.utcnow().isoformat()
    }
    
    response = test_client.post(
        "/api/v1/sync/push",
        json=push_request,
        headers=operator_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["processed_count"] == 0
    assert len(data["failed_changes"]) == 0
    assert len(data["conflicts"]) == 1


def test_push_no_authentication(test_client):
    """Test push without authentication."""
    push_request = {
        "changes": [],
        "client_timestamp": datetime.utcnow().isoformat()
    }
    
    response = test_client.post(
        "/api/v1/sync/push",
        json=push_request
    )
    
    assert response.status_code == 401


def test_pull_changes_operator(test_client, operator_auth_headers, test_pen):
    """Test pull changes as operator."""
    # Create some test data
    voter = Voter(
        pen_id=test_pen.id,
        voter_number="12345",
        full_name="Test Voter",
        has_voted=True,
        updated_at=datetime.utcnow()
    )
    
    # Get session from dependency override
    def get_test_session():
        for override in test_client.app.dependency_overrides.values():
            return next(override())
    
    session = get_test_session()
    session.add(voter)
    session.commit()
    
    response = test_client.get(
        "/api/v1/sync/pull",
        headers=operator_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "changes" in data
    assert "server_timestamp" in data
    assert "has_more" in data
    assert "total_available" in data
    
    # Should contain the voter we created
    voter_changes = [c for c in data["changes"] if c["entity_type"] == "Voter"]
    assert len(voter_changes) >= 1


def test_pull_changes_admin(test_client, admin_auth_headers, test_pen):
    """Test pull changes as admin (should see more entity types)."""
    # Create some test data
    voter = Voter(
        pen_id=test_pen.id,
        voter_number="12345",
        full_name="Test Voter",
        has_voted=True,
        updated_at=datetime.utcnow()
    )
    
    # Get session from dependency override
    def get_test_session():
        for override in test_client.app.dependency_overrides.values():
            return next(override())
    
    session = get_test_session()
    session.add(voter)
    session.commit()
    
    response = test_client.get(
        "/api/v1/sync/pull",
        headers=admin_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "changes" in data
    # Admin should see more entity types including User, Pen, etc.
    entity_types = {c["entity_type"] for c in data["changes"]}
    assert "Voter" in entity_types


def test_pull_changes_pagination(test_client, operator_auth_headers):
    """Test pull changes with pagination."""
    response = test_client.get(
        "/api/v1/sync/pull?limit=10&offset=0",
        headers=operator_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["changes"]) <= 10
    assert "has_more" in data


def test_pull_changes_last_sync_filter(test_client, operator_auth_headers):
    """Test pull changes with last_sync timestamp filter."""
    last_sync = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    
    response = test_client.get(
        f"/api/v1/sync/pull?last_sync={last_sync}",
        headers=operator_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned changes should be newer than last_sync
    for change in data["changes"]:
        change_timestamp = datetime.fromisoformat(change["timestamp"])
        assert change_timestamp > datetime.fromisoformat(last_sync)


def test_sync_stats(test_client, operator_auth_headers):
    """Test sync statistics endpoint."""
    response = test_client.get(
        "/api/v1/sync/stats",
        headers=operator_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "pending_push_count" in data
    assert "sync_enabled" in data
    assert data["sync_enabled"] is True


def test_sync_stats_no_auth(test_client):
    """Test sync stats without authentication."""
    response = test_client.get("/api/v1/sync/stats")
    
    assert response.status_code == 401 