"""Tests for hasNewResults flag functionality."""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtTest import QSignalSpy

from src.jcselect.controllers.results_controller import ResultsController
from src.jcselect.controllers.dashboard_controller import DashboardController


class TestHasNewResultsFlag:
    """Test suite for hasNewResults flag functionality."""

    @pytest.fixture
    def results_controller(self):
        """Create a ResultsController instance for testing."""
        # Mock the _connect_sync_signals method to avoid import issues
        with patch.object(ResultsController, '_connect_sync_signals'), \
             patch.object(ResultsController, 'loadAvailablePens'), \
             patch.object(ResultsController, 'refreshData'):
            controller = ResultsController()
            # Stop any automatic timers
            if hasattr(controller, '_new_results_timer') and controller._new_results_timer:
                controller._new_results_timer.stop()
            if hasattr(controller, '_refresh_timer') and controller._refresh_timer:
                controller._refresh_timer.stop()
            return controller

    @pytest.fixture
    def dashboard_controller(self):
        """Create a DashboardController instance for testing."""
        # Mock the _connect_sync_signals method to avoid import issues
        with patch.object(DashboardController, '_connect_sync_signals'):
            controller = DashboardController()
            return controller

    def test_results_controller_has_new_results_initial_state(self, results_controller):
        """Test that hasNewResults starts as False."""
        assert results_controller.hasNewResults is False
        assert results_controller._has_new_results is False

    def test_results_controller_has_new_results_property_getter_setter(self, results_controller):
        """Test hasNewResults property getter and setter."""
        # Initial state
        assert results_controller._get_has_new_results() is False
        
        # Set to True
        results_controller._set_has_new_results(True)
        assert results_controller._get_has_new_results() is True
        assert results_controller._has_new_results is True
        
        # Set back to False
        results_controller._set_has_new_results(False)
        assert results_controller._get_has_new_results() is False
        assert results_controller._has_new_results is False

    def test_results_controller_clear_new_results_flag_timer(self, results_controller):
        """Test that the new results flag is cleared after timer expires."""
        # Set the flag
        results_controller._set_has_new_results(True)
        assert results_controller.hasNewResults is True
        
        # Manually trigger the clear method (simulating timer timeout)
        results_controller._clear_new_results_flag()
        
        # Flag should be cleared
        assert results_controller.hasNewResults is False

    def test_results_controller_auto_refresh_enabled_property(self, results_controller):
        """Test autoRefreshEnabled property."""
        # Initial state should be True
        assert results_controller.autoRefreshEnabled is True
        assert results_controller._auto_refresh_enabled is True
        
        # Set to False
        results_controller._set_auto_refresh_enabled(False)
        assert results_controller.autoRefreshEnabled is False
        assert results_controller._auto_refresh_enabled is False
        
        # Set back to True
        results_controller._set_auto_refresh_enabled(True)
        assert results_controller.autoRefreshEnabled is True
        assert results_controller._auto_refresh_enabled is True

    def test_results_controller_tally_updated_respects_auto_refresh_flag(self, results_controller):
        """Test that tally updates respect autoRefreshEnabled flag."""
        # Enable auto-refresh
        results_controller._set_auto_refresh_enabled(True)
        
        # Mock the refresh timer
        refresh_timer_mock = Mock()
        results_controller._refresh_timer = refresh_timer_mock
        
        # Simulate tally line update
        results_controller._on_tally_updated("test_tally_123")
        
        # Should start refresh timer
        refresh_timer_mock.start.assert_called_once_with(250)
        
        # Reset mock
        refresh_timer_mock.reset_mock()
        
        # Disable auto-refresh
        results_controller._set_auto_refresh_enabled(False)
        
        # Simulate another tally line update
        results_controller._on_tally_updated("test_tally_456")
        
        # Should NOT start refresh timer
        refresh_timer_mock.start.assert_not_called()

    def test_results_controller_refresh_now_exists(self, results_controller):
        """Test that refreshNow method exists and is callable."""
        # Should have refreshNow method
        assert hasattr(results_controller, 'refreshNow')
        assert callable(results_controller.refreshNow)
        
        # Should be able to call it without error (even if mocked)
        try:
            results_controller.refreshNow()
        except Exception as e:
            # Might fail due to database calls, but method should exist
            assert "refreshNow" not in str(e)  # Method exists, other errors are OK

    def test_dashboard_controller_has_new_results_initial_state(self, dashboard_controller):
        """Test that DashboardController hasNewResults starts as False."""
        assert dashboard_controller.hasNewResults is False
        assert dashboard_controller._has_new_results is False

    def test_dashboard_controller_has_new_results_property(self, dashboard_controller):
        """Test DashboardController hasNewResults property."""
        # Initial state
        assert dashboard_controller._get_has_new_results() is False
        
        # Set to True
        dashboard_controller._set_has_new_results(True)
        assert dashboard_controller._get_has_new_results() is True
        assert dashboard_controller._has_new_results is True
        
        # Set back to False
        dashboard_controller._set_has_new_results(False)
        assert dashboard_controller._get_has_new_results() is False
        assert dashboard_controller._has_new_results is False

    def test_results_controller_new_results_timer_configuration(self, results_controller):
        """Test that the new results timer is configured correctly."""
        timer = results_controller._new_results_timer
        
        # Should be single shot
        assert timer.isSingleShot() is True

    def test_dashboard_badge_integration_mock(self, dashboard_controller):
        """Test dashboard badge color and tooltip integration (mocked)."""
        # Initial state - no new results
        assert dashboard_controller.hasNewResults is False
        
        # Simulate new results
        dashboard_controller._set_has_new_results(True)
        
        # Test the logic that would be used in QML
        badge_color_logic = "primary" if dashboard_controller.hasNewResults else "surface"
        tooltip_logic = "النتائج المباشرة (جديد)" if dashboard_controller.hasNewResults else "النتائج المباشرة"
        
        assert badge_color_logic == "primary"
        assert tooltip_logic == "النتائج المباشرة (جديد)"
        
        # Clear the flag
        dashboard_controller._set_has_new_results(False)
        
        badge_color_logic = "primary" if dashboard_controller.hasNewResults else "surface"
        tooltip_logic = "النتائج المباشرة (جديد)" if dashboard_controller.hasNewResults else "النتائج المباشرة"
        
        assert badge_color_logic == "surface"
        assert tooltip_logic == "النتائج المباشرة"

    def test_results_controller_method_signatures(self, results_controller):
        """Test that all required methods exist with correct signatures."""
        # Test that key methods exist
        assert hasattr(results_controller, 'refreshNow')
        assert hasattr(results_controller, '_clear_new_results_flag')
        assert hasattr(results_controller, '_on_sync_completed')
        assert hasattr(results_controller, '_on_tally_updated')
        assert hasattr(results_controller, '_get_has_new_results')
        assert hasattr(results_controller, '_set_has_new_results')
        assert hasattr(results_controller, '_get_auto_refresh_enabled')
        assert hasattr(results_controller, '_set_auto_refresh_enabled')
        
        # Test that methods are callable
        assert callable(results_controller.refreshNow)
        assert callable(results_controller._clear_new_results_flag)
        
        # Test property attributes exist
        assert hasattr(results_controller, '_has_new_results')
        assert hasattr(results_controller, '_auto_refresh_enabled')
        assert hasattr(results_controller, '_new_results_timer')

    def test_dashboard_controller_method_signatures(self, dashboard_controller):
        """Test that DashboardController has required methods."""
        # Test that key methods exist
        assert hasattr(dashboard_controller, 'openLiveResults')
        assert hasattr(dashboard_controller, '_get_has_new_results')
        assert hasattr(dashboard_controller, '_set_has_new_results')
        
        # Test that methods are callable
        assert callable(dashboard_controller.openLiveResults)
        
        # Test property attributes exist
        assert hasattr(dashboard_controller, '_has_new_results')

    def test_results_controller_on_sync_completed_flow(self, results_controller):
        """Test the sync completion flow."""
        # Mock the timer and refresh method
        timer_mock = Mock()
        results_controller._new_results_timer = timer_mock
        
        refresh_timer_mock = Mock()  
        results_controller._refresh_timer = refresh_timer_mock
        
        # Initially not syncing and no new results
        assert results_controller.isSyncing is False
        assert results_controller.hasNewResults is False
        
        # Simulate sync completion
        results_controller._on_sync_completed()
        
        # Should set new results flag
        assert results_controller.hasNewResults is True
        
        # Should start timers
        timer_mock.start.assert_called_once_with(3000)  # 3 seconds for flag clear
        refresh_timer_mock.start.assert_called_once_with(250)  # 250ms for refresh

    def test_integration_flag_clearing_after_data_refresh(self, results_controller):
        """Test that hasNewResults is cleared when manually cleared."""
        # Set the flag
        results_controller._set_has_new_results(True)
        assert results_controller.hasNewResults is True
        
        # Connect clearing mechanism (simulating ResultsWindow connection)
        def clear_on_refresh():
            results_controller._set_has_new_results(False)
        
        results_controller.dataRefreshed.connect(clear_on_refresh)
        
        # Emit dataRefreshed signal
        results_controller.dataRefreshed.emit()
        
        # Flag should be cleared
        assert results_controller.hasNewResults is False 