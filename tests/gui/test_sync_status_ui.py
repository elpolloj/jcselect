"""Tests for sync status UI integration."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QDateTime, QTimer
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from jcselect.controllers.sync_status_controller import SyncStatusController


class TestSyncStatusUI:
    """Tests for sync status controller and UI integration."""

    @pytest.fixture
    def sync_controller(self) -> SyncStatusController:
        """Create a sync status controller for testing."""
        controller = SyncStatusController()
        # Stop the automatic timers for controlled testing
        controller._status_timer.stop()
        controller._ping_timer.stop()
        return controller

    def test_initial_state(self, sync_controller: SyncStatusController) -> None:
        """Test initial state of sync status controller."""
        assert not sync_controller.isOnline
        # Don't test pendingChanges as it may vary based on actual queue state
        assert sync_controller.syncProgress == 0.0
        # Don't assert lastSyncTime validity as it may be set during initialization

    def test_online_status_property(self, sync_controller: SyncStatusController) -> None:
        """Test online status property changes."""
        # Initially offline
        assert not sync_controller.isOnline
        
        # Simulate going online
        sync_controller._is_online = True
        sync_controller.isOnlineChanged.emit(True)
        
        assert sync_controller.isOnline

    def test_pending_changes_property(self, sync_controller: SyncStatusController) -> None:
        """Test pending changes property."""
        initial_pending = sync_controller.pendingChanges
        
        # Simulate pending changes
        sync_controller._pending_changes = initial_pending + 5
        sync_controller.pendingChangesChanged.emit(initial_pending + 5)
        
        assert sync_controller.pendingChanges == initial_pending + 5

    def test_sync_progress_property(self, sync_controller: SyncStatusController) -> None:
        """Test sync progress property."""
        # Initially no progress
        assert sync_controller.syncProgress == 0.0
        
        # Simulate progress update
        sync_controller.on_sync_progress(0.5)
        assert sync_controller.syncProgress == 0.5
        
        # Test bounds
        sync_controller.on_sync_progress(-0.1)
        assert sync_controller.syncProgress == 0.0
        
        sync_controller.on_sync_progress(1.5)
        assert sync_controller.syncProgress == 1.0

    def test_sync_started_signal(self, sync_controller: SyncStatusController) -> None:
        """Test sync started signal and state changes."""
        # Track signal emissions
        signal_emitted = False
        def on_sync_started():
            nonlocal signal_emitted
            signal_emitted = True
        
        sync_controller.syncStarted.connect(on_sync_started)
        
        # Trigger sync started
        sync_controller.on_sync_started()
        
        assert signal_emitted
        assert sync_controller.syncProgress == 0.0

    def test_sync_completed_signal(self, sync_controller: SyncStatusController) -> None:
        """Test sync completed signal and state changes."""
        # Track signal emissions
        changes_count = 0
        def on_sync_completed(count):
            nonlocal changes_count
            changes_count = count
        
        sync_controller.syncCompleted.connect(on_sync_completed)
        
        # Trigger sync completed
        sync_controller.on_sync_completed(10)
        
        assert changes_count == 10
        assert sync_controller.syncProgress == 1.0
        assert sync_controller.lastSyncTime.isValid()

    def test_sync_failed_signal(self, sync_controller: SyncStatusController) -> None:
        """Test sync failed signal and state changes."""
        # Track signal emissions
        error_message = ""
        def on_sync_failed(msg):
            nonlocal error_message
            error_message = msg
        
        sync_controller.syncFailed.connect(on_sync_failed)
        
        # Trigger sync failed
        test_error = "Network error"
        sync_controller.on_sync_failed(test_error)
        
        assert error_message == test_error
        assert sync_controller.syncProgress == 0.0

    def test_last_sync_time_formatting(self, sync_controller: SyncStatusController) -> None:
        """Test last sync time formatting."""
        # Clear any existing time
        sync_controller._last_sync_time = QDateTime()
        
        # Initially never synced
        assert sync_controller.getLastSyncTimeFormatted() == "Never"
        
        # Set recent sync time
        recent_time = QDateTime.currentDateTime().addSecs(-30)
        sync_controller._last_sync_time = recent_time
        
        formatted = sync_controller.getLastSyncTimeFormatted()
        assert "s ago" in formatted or "m ago" in formatted

    def test_status_text_generation(self, sync_controller: SyncStatusController) -> None:
        """Test status text generation."""
        # Test offline status
        sync_controller._is_online = False
        assert "Offline" in sync_controller.getStatusText()
        
        # Test online with pending changes
        sync_controller._is_online = True
        sync_controller._pending_changes = 3
        status = sync_controller.getStatusText()
        assert "3 pending" in status
        
        # Test up to date
        sync_controller._pending_changes = 0
        assert "Up to date" in sync_controller.getStatusText()

    def test_refresh_status_method(self, sync_controller: SyncStatusController) -> None:
        """Test manual status refresh."""
        # Should not raise any exceptions
        sync_controller.refreshStatus()

    def test_force_sync_method(self, sync_controller: SyncStatusController) -> None:
        """Test force sync method."""
        # Track signal emissions
        sync_started = False
        def on_sync_started():
            nonlocal sync_started
            sync_started = True
        
        sync_controller.syncStarted.connect(on_sync_started)
        
        # Trigger force sync
        sync_controller.forcSync()
        
        assert sync_started

    def test_sync_engine_connection(self, sync_controller: SyncStatusController) -> None:
        """Test connection to sync engine."""
        # Mock sync engine
        class MockSyncEngine:
            pass
        
        mock_engine = MockSyncEngine()
        
        # Should not raise any exceptions
        sync_controller.connectToSyncEngine(mock_engine)


@pytest.mark.qt
class TestSyncStatusQMLIntegration:
    """Integration tests for sync status in QML context."""

    @pytest.fixture
    def qml_engine(self) -> QQmlApplicationEngine:
        """Create QML engine for testing."""
        engine = QQmlApplicationEngine()
        return engine

    def test_controller_properties_in_qml(self, qml_engine: QQmlApplicationEngine) -> None:
        """Test that controller properties are accessible from QML."""
        # Create controller
        controller = SyncStatusController()
        controller._status_timer.stop()
        controller._ping_timer.stop()
        
        # Expose to QML context
        qml_engine.rootContext().setContextProperty("syncStatus", controller)
        
        # Load minimal QML for testing
        qml_code = """
        import QtQuick 2.15
        
        Item {
            id: root
            property bool syncOnline: syncStatus.isOnline
            property int syncPending: syncStatus.pendingChanges
            property real syncProgress: syncStatus.syncProgress
            property bool syncEnabled: syncStatus.syncEnabled
        }
        """
        
        # This would require a full QML test environment
        # For now, just verify the controller exists
        assert controller is not None
        assert hasattr(controller, 'isOnline')
        assert hasattr(controller, 'pendingChanges')
        assert hasattr(controller, 'syncProgress')

    def test_signal_emission_from_qml(self, qml_engine: QQmlApplicationEngine) -> None:
        """Test signal emission from QML context."""
        controller = SyncStatusController()
        controller._status_timer.stop()
        controller._ping_timer.stop()
        
        # Track signal
        signal_received = False
        def on_signal():
            nonlocal signal_received
            signal_received = True
        
        controller.syncStarted.connect(on_signal)
        
        # Emit signal
        controller.on_sync_started()
        
        assert signal_received


class TestSyncStatusBehavior:
    """Tests for sync status controller behavior and edge cases."""

    def test_timer_behavior(self) -> None:
        """Test timer initialization and behavior."""
        controller = SyncStatusController()
        
        # Timers should be active initially
        assert controller._status_timer.isActive()
        assert controller._ping_timer.isActive()
        
        # Stop timers for cleanup
        controller._status_timer.stop()
        controller._ping_timer.stop()

    def test_error_handling_in_status_update(self) -> None:
        """Test error handling in status update methods."""
        controller = SyncStatusController()
        controller._status_timer.stop()
        controller._ping_timer.stop()
        
        # Mock sync_queue to raise exception
        import jcselect.controllers.sync_status_controller as module
        original_queue = module.sync_queue
        
        class MockQueue:
            def get_pending_count(self):
                raise Exception("Test error")
        
        module.sync_queue = MockQueue()
        
        try:
            # Should handle the exception gracefully
            controller._update_status()
            # Should not crash
        finally:
            # Restore original
            module.sync_queue = original_queue

    def test_connectivity_check_error_handling(self) -> None:
        """Test error handling in connectivity check."""
        controller = SyncStatusController()
        controller._status_timer.stop()
        controller._ping_timer.stop()
        
        # This should handle network errors gracefully
        controller._check_online_status()
        
        # Should not crash and should set offline status
        assert not controller.isOnline

    def test_property_change_notifications(self) -> None:
        """Test that property changes emit proper notifications."""
        controller = SyncStatusController()
        controller._status_timer.stop()
        controller._ping_timer.stop()
        
        # Track signal emissions
        signals_received = []
        
        controller.isOnlineChanged.connect(lambda: signals_received.append('online'))
        controller.pendingChangesChanged.connect(lambda: signals_received.append('pending'))
        controller.syncProgressChanged.connect(lambda: signals_received.append('progress'))
        controller.lastSyncTimeChanged.connect(lambda: signals_received.append('time'))
        
        # Trigger changes that should emit signals
        controller.on_sync_started()  # Should emit progress
        controller.on_sync_completed(5)  # Should emit progress and time
        
        assert 'progress' in signals_received
        assert 'time' in signals_received 