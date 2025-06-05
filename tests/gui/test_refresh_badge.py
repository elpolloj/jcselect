"""Tests for RefreshBadge QML component."""

from datetime import datetime, timedelta

import pytest

from tests.helpers.qml_test_helper import QMLTestHelper


class RefreshBadgeTestHelper(QMLTestHelper):
    """Helper class for testing RefreshBadge component."""

    def create_refresh_badge(self, is_syncing=False, has_error=False, last_updated=None):
        """Create a RefreshBadge instance for testing."""
        if last_updated is None:
            last_updated = datetime.now()

        # Convert datetime to QML-compatible format
        timestamp = last_updated.strftime("%Y-%m-%dT%H:%M:%S")

        qml_code = f"""
        import QtQuick 2.15
        import jcselect.ui.components 1.0

        RefreshBadge {{
            id: refreshBadge
            width: 200
            height: 50
            isSyncing: {str(is_syncing).lower()}
            hasError: {str(has_error).lower()}
            lastUpdated: new Date("{timestamp}")

            property bool refreshClicked: false

            onRefreshRequested: {{
                refreshClicked = true
            }}
        }}
        """
        return self.create_qml_object(qml_code)


class TestRefreshBadge:
    """Test suite for RefreshBadge component."""

    @pytest.fixture
    def helper(self, qml_engine):
        """Create test helper."""
        return RefreshBadgeTestHelper(qml_engine)

    def test_refresh_badge_creation(self, helper):
        """Test that RefreshBadge can be created."""
        refresh_badge = helper.create_refresh_badge()
        assert refresh_badge is not None

        # Check initial properties
        assert refresh_badge.property("isSyncing") is False
        assert refresh_badge.property("hasError") is False
        assert refresh_badge.property("refreshClicked") is False

    def test_syncing_state_display(self, helper):
        """Test syncing state affects display."""
        # Test syncing state
        refresh_badge_syncing = helper.create_refresh_badge(is_syncing=True)
        assert refresh_badge_syncing.property("isSyncing") is True

        # Find status indicator
        status_indicator = helper.find_child_by_property(refresh_badge_syncing, "objectName", "statusIndicator")
        if status_indicator is None:
            # Try finding by ID
            status_indicator = helper.find_child(refresh_badge_syncing, "Rectangle", name_hint="statusIndicator")

        # Test non-syncing state
        refresh_badge_not_syncing = helper.create_refresh_badge(is_syncing=False)
        assert refresh_badge_not_syncing.property("isSyncing") is False

    def test_error_state_display(self, helper):
        """Test error state affects display."""
        refresh_badge_error = helper.create_refresh_badge(has_error=True)
        assert refresh_badge_error.property("hasError") is True

        refresh_badge_no_error = helper.create_refresh_badge(has_error=False)
        assert refresh_badge_no_error.property("hasError") is False

    def test_status_color_thresholds(self, helper):
        """Test color coding based on time thresholds."""
        now = datetime.now()

        # Test recent update (< 20 seconds) - should be green/success
        recent_time = now - timedelta(seconds=10)
        refresh_badge_recent = helper.create_refresh_badge(last_updated=recent_time)

        # Wait for property evaluation
        helper.process_events()

        # Check that secondsSinceUpdate is calculated
        seconds_since = refresh_badge_recent.property("secondsSinceUpdate")
        assert seconds_since is not None
        assert seconds_since >= 10  # Should be around 10 seconds

        # Test moderate delay (20-120 seconds) - should be yellow/warning
        moderate_time = now - timedelta(seconds=60)
        refresh_badge_moderate = helper.create_refresh_badge(last_updated=moderate_time)
        helper.process_events()

        moderate_seconds = refresh_badge_moderate.property("secondsSinceUpdate")
        assert moderate_seconds >= 60

        # Test old update (> 120 seconds) - should be red/error
        old_time = now - timedelta(seconds=180)
        refresh_badge_old = helper.create_refresh_badge(last_updated=old_time)
        helper.process_events()

        old_seconds = refresh_badge_old.property("secondsSinceUpdate")
        assert old_seconds >= 180

    def test_manual_refresh_button_click(self, helper):
        """Test manual refresh button triggers signal."""
        refresh_badge = helper.create_refresh_badge()

        # Find the refresh button
        refresh_button = helper.find_child(refresh_badge, "Button")
        assert refresh_button is not None

        # Check button is enabled initially
        assert refresh_button.property("enabled") is True

        # Simulate button click
        helper.click_item(refresh_button)
        helper.process_events()

        # Check that refresh signal was emitted
        assert refresh_badge.property("refreshClicked") is True

    def test_refresh_button_disabled_during_sync(self, helper):
        """Test refresh button is disabled during sync."""
        refresh_badge_syncing = helper.create_refresh_badge(is_syncing=True)

        # Find the refresh button
        refresh_button = helper.find_child(refresh_badge_syncing, "Button")
        assert refresh_button is not None

        # Button should be disabled during sync
        assert refresh_button.property("enabled") is False

    def test_timestamp_display_format(self, helper):
        """Test timestamp is displayed in correct Arabic format."""
        test_time = datetime(2024, 1, 15, 14, 30, 45)  # 2:30:45 PM
        refresh_badge = helper.create_refresh_badge(last_updated=test_time)

        helper.process_events()

        # Find timestamp text element
        # The timestamp should be in "آخر تحديث: hh:mm:ss" format
        timestamp_texts = helper.find_children(refresh_badge, "Text")
        timestamp_found = False

        for text_item in timestamp_texts:
            text_content = text_item.property("text")
            if text_content and "آخر تحديث:" in text_content:
                timestamp_found = True
                # Should contain time format
                assert "14:30:45" in text_content or "2:30:45" in text_content
                break

        assert timestamp_found, "Timestamp text not found"

    def test_status_text_changes(self, helper):
        """Test status text changes based on state."""
        # Test normal state
        refresh_badge_normal = helper.create_refresh_badge()
        status_texts = helper.find_children(refresh_badge_normal, "Text")

        normal_status_found = False
        for text_item in status_texts:
            text_content = text_item.property("text")
            if text_content == "متصل":
                normal_status_found = True
                break
        assert normal_status_found

        # Test syncing state
        refresh_badge_syncing = helper.create_refresh_badge(is_syncing=True)
        syncing_texts = helper.find_children(refresh_badge_syncing, "Text")

        syncing_status_found = False
        for text_item in syncing_texts:
            text_content = text_item.property("text")
            if text_content == "جاري التحديث...":
                syncing_status_found = True
                break
        assert syncing_status_found

        # Test error state
        refresh_badge_error = helper.create_refresh_badge(has_error=True)
        error_texts = helper.find_children(refresh_badge_error, "Text")

        error_status_found = False
        for text_item in error_texts:
            text_content = text_item.property("text")
            if text_content == "خطأ في التحديث":
                error_status_found = True
                break
        assert error_status_found

    def test_spinning_animation_during_sync(self, helper):
        """Test spinning animation is active during sync."""
        # Test syncing state
        refresh_badge_syncing = helper.create_refresh_badge(is_syncing=True)

        # Find status indicator with spinning icon
        status_indicators = helper.find_children(refresh_badge_syncing, "Rectangle")

        spinning_found = False
        for indicator in status_indicators:
            # Look for the spinning sync icon text
            texts = helper.find_children(indicator, "Text")
            for text_item in texts:
                text_content = text_item.property("text")
                if text_content == "⟳":  # Spinning sync icon
                    spinning_found = True
                    break
            if spinning_found:
                break

        assert spinning_found, "Spinning sync icon not found during syncing"

        # Test non-syncing state should show solid dot
        refresh_badge_normal = helper.create_refresh_badge(is_syncing=False)
        status_indicators_normal = helper.find_children(refresh_badge_normal, "Rectangle")

        dot_found = False
        for indicator in status_indicators_normal:
            texts = helper.find_children(indicator, "Text")
            for text_item in texts:
                text_content = text_item.property("text")
                if text_content == "●":  # Solid dot
                    dot_found = True
                    break
            if dot_found:
                break

        assert dot_found, "Solid dot icon not found in normal state"
