"""Unit tests for sync settings configuration."""

import pytest
from jcselect.utils.settings import SyncSettings
from pydantic import ValidationError


def test_sync_settings_defaults_valid():
    """Test that SyncSettings with minimal required values has valid defaults."""
    settings = SyncSettings(
        sync_api_url="https://api.example.com",
        sync_jwt_secret="x" * 32
    )

    assert settings.sync_enabled is True
    assert settings.sync_interval_seconds == 300
    assert settings.sync_max_payload_size == 1_048_576
    assert settings.sync_pull_page_size == 100
    assert settings.sync_max_pull_pages == 10
    assert settings.sync_max_retries == 5
    assert settings.sync_backoff_base == 2.0
    assert settings.sync_backoff_max_seconds == 300
    assert settings.sync_entity_order == [
        "User", "Party", "Pen",
        "TallySession",
        "Voter", "TallyLine",
        "AuditLog",
    ]


def test_sync_settings_validation_constraints():
    """Test validation constraints on sync settings fields."""
    valid_base = {
        "sync_api_url": "https://api.example.com",
        "sync_jwt_secret": "x" * 32
    }

    # Test JWT secret minimum length
    with pytest.raises(ValidationError, match="at least 32 characters"):
        SyncSettings(sync_api_url="https://api.example.com", sync_jwt_secret="short")

    # Test interval bounds
    with pytest.raises(ValidationError, match="greater than or equal to 60"):
        SyncSettings(**valid_base, sync_interval_seconds=30)

    with pytest.raises(ValidationError, match="less than or equal to 3600"):
        SyncSettings(**valid_base, sync_interval_seconds=4000)

    # Test payload size bounds
    with pytest.raises(ValidationError, match="greater than or equal to 1024"):
        SyncSettings(**valid_base, sync_max_payload_size=500)

    with pytest.raises(ValidationError, match="less than or equal to 10485760"):
        SyncSettings(**valid_base, sync_max_payload_size=20_000_000)

    # Test page size bounds
    with pytest.raises(ValidationError, match="greater than or equal to 10"):
        SyncSettings(**valid_base, sync_pull_page_size=5)

    with pytest.raises(ValidationError, match="less than or equal to 1000"):
        SyncSettings(**valid_base, sync_pull_page_size=2000)


def test_sync_settings_env_override(monkeypatch):
    """Test that environment variables override default values."""
    # Set environment variables
    monkeypatch.setenv("SYNC_API_URL", "https://test.example.com")
    monkeypatch.setenv("SYNC_JWT_SECRET", "test-secret-32-characters-long-!")
    monkeypatch.setenv("SYNC_INTERVAL_SECONDS", "600")
    monkeypatch.setenv("SYNC_ENABLED", "false")
    monkeypatch.setenv("SYNC_PULL_PAGE_SIZE", "50")
    monkeypatch.setenv("SYNC_MAX_RETRIES", "3")
    monkeypatch.setenv("SYNC_BACKOFF_BASE", "1.5")

    # Create settings instance (should pick up env vars)
    settings = SyncSettings()

    # Note: pydantic HttpUrl normalizes URLs by adding trailing slash
    assert str(settings.sync_api_url) == "https://test.example.com/"
    assert settings.sync_jwt_secret == "test-secret-32-characters-long-!"
    assert settings.sync_interval_seconds == 600
    assert settings.sync_enabled is False
    assert settings.sync_pull_page_size == 50
    assert settings.sync_max_retries == 3
    assert settings.sync_backoff_base == 1.5


def test_sync_settings_required_fields(monkeypatch):
    """Test that required fields raise errors when missing."""
    # Clear any existing env vars that might interfere
    monkeypatch.delenv("SYNC_API_URL", raising=False)
    monkeypatch.delenv("SYNC_JWT_SECRET", raising=False)

    # Missing sync_api_url
    with pytest.raises(ValidationError, match="sync_api_url"):
        SyncSettings(sync_jwt_secret="x" * 32)

    # Missing sync_jwt_secret
    with pytest.raises(ValidationError, match="sync_jwt_secret"):
        SyncSettings(sync_api_url="https://api.example.com")


def test_sync_settings_url_validation():
    """Test that sync_api_url field validates URLs properly."""
    # Valid URLs should work (note: pydantic adds trailing slash)
    valid_urls = [
        ("https://api.example.com", "https://api.example.com/"),
        ("https://localhost:8000", "https://localhost:8000/"),
        ("http://192.168.1.100:3000/api", "http://192.168.1.100:3000/api"),
    ]

    for input_url, expected_url in valid_urls:
        settings = SyncSettings(sync_api_url=input_url, sync_jwt_secret="x" * 32)
        assert str(settings.sync_api_url) == expected_url

    # Invalid URLs should fail
    with pytest.raises(ValidationError, match="URL"):
        SyncSettings(sync_api_url="not-a-url", sync_jwt_secret="x" * 32)


def test_sync_entity_order_default():
    """Test that sync_entity_order has the correct default dependency order."""
    settings = SyncSettings(
        sync_api_url="https://api.example.com",
        sync_jwt_secret="x" * 32
    )

    # Verify dependency order: parents before children
    order = settings.sync_entity_order

    # User, Party, Pen should come before entities that reference them
    user_idx = order.index("User")
    party_idx = order.index("Party")
    pen_idx = order.index("Pen")

    tally_session_idx = order.index("TallySession")
    voter_idx = order.index("Voter")
    tally_line_idx = order.index("TallyLine")
    audit_log_idx = order.index("AuditLog")

    # Parents should come before children
    assert user_idx < voter_idx  # Users before Voters (voted_by_operator_id)
    assert user_idx < tally_session_idx  # Users before TallySessions (operator_id)
    assert user_idx < audit_log_idx  # Users before AuditLogs (operator_id)

    assert party_idx < tally_line_idx  # Parties before TallyLines (party_id)
    assert pen_idx < voter_idx  # Pens before Voters (pen_id)
    assert pen_idx < tally_session_idx  # Pens before TallySessions (pen_id)

    assert tally_session_idx < tally_line_idx  # TallySessions before TallyLines (tally_session_id)

    # AuditLog should be last (references everything)
    assert audit_log_idx == len(order) - 1
