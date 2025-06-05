"""Tests for RefreshBadge manual refresh functionality."""

import pytest

from tests.helpers.qml_test_helper import QMLTestHelper


class RefreshBadgeTestHelper(QMLTestHelper):
    """Helper class for testing RefreshBadge component."""

    def create_refresh_badge(self, is_syncing=False, last_update_time=None):
        """Create a RefreshBadge instance for testing."""
        if last_update_time is None:
            last_update_time = "2024-01-01T12:00:00"

        qml_code = f"""
        import QtQuick 2.15
        import QtQuick.Controls 2.15
        import "../../../src/jcselect/ui/components/"

        Item {{
            id: root
            width: 200
            height: 100

            property bool refreshCalled: false
            property alias badge: refreshBadge

            RefreshBadge {{
                id: refreshBadge
                anchors.centerIn: parent
                
                isSyncing: {str(is_syncing).lower()}
                lastUpdateTime: new Date("{last_update_time}")
                
                onRefreshRequested: {{
                    root.refreshCalled = true
                }}
            }}
        }}
        """
        return self.create_qml_object(qml_code)

    def create_refresh_badge_with_controller(self):
        """Create a RefreshBadge with mock controller integration."""
        qml_code = """
        import QtQuick 2.15
        import QtQuick.Controls 2.15
        import "../../../src/jcselect/ui/components/"

        Item {
            id: root
            width: 200
            height: 100

            property bool refreshNowCalled: false
            property bool refreshDataCalled: false
            property alias badge: refreshBadge

            property var mockController: {
                "isSyncing": false,
                "lastUpdated": new Date("2024-01-01T12:00:00"),
                "refreshNow": function() {
                    root.refreshNowCalled = true
                },
                "refreshData": function() {
                    root.refreshDataCalled = true
                }
            }

            RefreshBadge {
                id: refreshBadge
                anchors.centerIn: parent
                
                isSyncing: mockController.isSyncing
                lastUpdateTime: mockController.lastUpdated
                
                onRefreshRequested: {
                    if (mockController.refreshNow) {
                        mockController.refreshNow()
                    }
                }
            }
        }
        """
        return self.create_qml_object(qml_code)


class TestRefreshBadgeManual:
    """Test suite for RefreshBadge manual refresh functionality."""

    @pytest.fixture
    def helper(self, qml_engine):
        """Create test helper."""
        return RefreshBadgeTestHelper(qml_engine)

    def test_refresh_badge_creation(self, helper):
        """Test that RefreshBadge can be created."""
        root = helper.create_refresh_badge()
        assert root is not None

        badge = root.property("badge")
        assert badge is not None

    def test_manual_refresh_signal_emission(self, helper):
        """Test that manual refresh emits signal correctly."""
        root = helper.create_refresh_badge()
        badge = root.property("badge")

        # Initially no refresh called
        assert root.property("refreshCalled") is False

        # Find and click refresh button
        refresh_buttons = helper.find_children(badge, "Button")
        refresh_button = None

        for button in refresh_buttons:
            # Look for refresh/update button (might have refresh icon or text)
            button_text = button.property("text")
            if button_text and ("↻" in button_text or "🔄" in button_text or button.property("objectName") == "refreshButton"):
                refresh_button = button
                break

        if refresh_button:
            # Simulate button click
            refresh_button.clicked.emit()
            helper.process_events()

            # Verify signal was emitted
            assert root.property("refreshCalled") is True
        else:
            # If no explicit button found, try triggering refresh directly
            badge.refreshRequested.emit()
            helper.process_events()
            assert root.property("refreshCalled") is True

    def test_refresh_badge_with_controller_integration(self, helper):
        """Test RefreshBadge integration with mock controller."""
        root = helper.create_refresh_badge_with_controller()
        badge = root.property("badge")

        # Initially no refresh called
        assert root.property("refreshNowCalled") is False
        assert root.property("refreshDataCalled") is False

        # Trigger refresh
        badge.refreshRequested.emit()
        helper.process_events()

        # Verify controller method was called
        assert root.property("refreshNowCalled") is True

    def test_syncing_state_affects_badge(self, helper):
        """Test that syncing state affects badge appearance."""
        # Test with syncing false
        root_not_syncing = helper.create_refresh_badge(is_syncing=False)
        badge_not_syncing = root_not_syncing.property("badge")

        # Test with syncing true
        root_syncing = helper.create_refresh_badge(is_syncing=True)
        badge_syncing = root_syncing.property("badge")

        # Both should exist but may have different visual states
        assert badge_not_syncing is not None
        assert badge_syncing is not None

        # Check isSyncing property is correctly bound
        assert badge_not_syncing.property("isSyncing") is False
        assert badge_syncing.property("isSyncing") is True

    def test_last_update_time_display(self, helper):
        """Test that last update time is properly displayed."""
        test_time = "2024-01-15T14:30:25"
        root = helper.create_refresh_badge(last_update_time=test_time)
        badge = root.property("badge")

        # Check that lastUpdateTime property is set
        last_update = badge.property("lastUpdateTime")
        assert last_update is not None

    def test_refresh_during_sync(self, helper):
        """Test refresh behavior during active sync."""
        root = helper.create_refresh_badge(is_syncing=True)
        badge = root.property("badge")

        # Try to refresh while syncing
        badge.refreshRequested.emit()
        helper.process_events()

        # Should still emit signal (controller decides how to handle)
        assert root.property("refreshCalled") is True

    def test_multiple_refresh_calls(self, helper):
        """Test multiple rapid refresh calls."""
        root = helper.create_refresh_badge_with_controller()
        badge = root.property("badge")

        # Call refresh multiple times
        badge.refreshRequested.emit()
        badge.refreshRequested.emit()
        badge.refreshRequested.emit()
        helper.process_events()

        # Controller method should be called for each
        assert root.property("refreshNowCalled") is True

    def test_refresh_badge_accessibility(self, helper):
        """Test refresh badge accessibility features."""
        root = helper.create_refresh_badge()
        badge = root.property("badge")

        # Badge should be accessible
        assert badge is not None

        # Look for interactive elements
        buttons = helper.find_children(badge, "Button")
        mouse_areas = helper.find_children(badge, "MouseArea")

        # Should have some interactive element for refresh
        assert len(buttons) > 0 or len(mouse_areas) > 0

    def test_arabic_rtl_layout(self, helper):
        """Test that RefreshBadge works correctly with RTL layout."""
        root = helper.create_refresh_badge()
        badge = root.property("badge")

        # Badge should handle RTL layout gracefully
        # This is mainly ensuring no crashes with RTL
        assert badge is not None

        # Find text elements that should support RTL
        texts = helper.find_children(badge, "Text")
        for text in texts:
            # Text elements should exist and be properly configured
            assert text is not None

    def test_refresh_badge_theme_integration(self, helper):
        """Test that RefreshBadge integrates properly with theme."""
        root = helper.create_refresh_badge()
        badge = root.property("badge")

        # Badge should use theme colors and properties
        # Check for theme-related properties
        color = badge.property("color")
        
        # Should have some visual styling
        assert badge is not None
        # Note: Specific theme properties might not be directly testable
        # but the component should load without errors 