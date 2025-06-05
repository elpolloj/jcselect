"""Sync status controller for exposing sync state to QML."""
from __future__ import annotations

from typing import Any

from loguru import logger
from PySide6.QtCore import Property, QDateTime, QObject, QTimer, Signal, Slot

from jcselect.sync.queue import sync_queue
from jcselect.utils.settings import sync_settings


class SyncStatusController(QObject):
    """Controller for managing and exposing sync status to QML."""

    # Signals
    isOnlineChanged = Signal(bool)
    lastSyncTimeChanged = Signal(QDateTime)
    pendingChangesChanged = Signal(int)
    syncProgressChanged = Signal(float)
    isSyncingChanged = Signal(bool)

    syncStarted = Signal()
    syncCompleted = Signal(int)  # number of changes synced
    syncFailed = Signal(str)     # error message

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the sync status controller."""
        super().__init__(parent)

        # Internal state
        self._is_online = False
        self._last_sync_time = QDateTime()
        self._pending_changes = 0
        self._sync_progress = 0.0
        self._is_syncing = False

        # Timer for periodic status updates
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(5000)  # Update every 5 seconds

        # Timer for checking online status
        self._ping_timer = QTimer(self)
        self._ping_timer.timeout.connect(self._check_online_status)
        self._ping_timer.start(30000)  # Check every 30 seconds

        # Initialize status
        self._update_status()

        logger.info("SyncStatusController initialized")

    @Property(bool, notify=isOnlineChanged)
    def isOnline(self) -> bool:
        """Get online status."""
        return self._is_online

    @Property(QDateTime, notify=lastSyncTimeChanged)
    def lastSyncTime(self) -> QDateTime:
        """Get last sync timestamp."""
        return self._last_sync_time

    @Property(int, notify=pendingChangesChanged)
    def pendingChanges(self) -> int:
        """Get number of pending changes to sync."""
        return self._pending_changes

    @Property(float, notify=syncProgressChanged)
    def syncProgress(self) -> float:
        """Get sync progress (0.0 to 1.0)."""
        return self._sync_progress

    @Property(bool, constant=True)
    def syncEnabled(self) -> bool:
        """Get whether sync is enabled."""
        return sync_settings.sync_enabled

    @Property(int, constant=True)
    def syncInterval(self) -> int:
        """Get sync interval in seconds."""
        return sync_settings.sync_interval_seconds

    @Property(bool, notify=isSyncingChanged)
    def isSyncing(self) -> bool:
        """Get whether sync is in progress."""
        return self._is_syncing

    @Slot()
    def refreshStatus(self) -> None:
        """Manually refresh sync status."""
        self._update_status()
        self._check_online_status()

    @Slot()
    def forcSync(self) -> None:
        """Force an immediate sync cycle."""
        # This would trigger a sync if we had direct access to the sync engine
        # For now, just update status
        logger.info("Force sync requested")
        self.syncStarted.emit()
        self._update_status()

    @Slot(result=str)
    def getLastSyncTimeFormatted(self) -> str:
        """Get formatted last sync time string."""
        if not self._last_sync_time.isValid():
            return "Never"

        now = QDateTime.currentDateTime()
        seconds_diff = self._last_sync_time.secsTo(now)

        if seconds_diff < 60:
            return f"{seconds_diff}s ago"
        elif seconds_diff < 3600:
            minutes = seconds_diff // 60
            return f"{minutes}m ago"
        elif seconds_diff < 86400:
            hours = seconds_diff // 3600
            return f"{hours}h ago"
        else:
            days = seconds_diff // 86400
            return f"{days}d ago"

    @Slot(result=str)
    def getStatusText(self) -> str:
        """Get human-readable status text."""
        if not sync_settings.sync_enabled:
            return "Sync disabled"

        if not self._is_online:
            return "Offline"

        if self._pending_changes > 0:
            return f"{self._pending_changes} pending"

        return "Up to date"

    def _update_status(self) -> None:
        """Update sync status from queue and settings."""
        try:
            # Get pending changes count
            new_pending = sync_queue.get_pending_count()
            if new_pending != self._pending_changes:
                self._pending_changes = new_pending
                self.pendingChangesChanged.emit(self._pending_changes)

            # Update last sync time (placeholder - would come from sync engine)
            # For now, use a mock timestamp if we have no pending changes
            if self._pending_changes == 0 and not self._last_sync_time.isValid():
                self._last_sync_time = QDateTime.currentDateTime()
                self.lastSyncTimeChanged.emit(self._last_sync_time)

        except Exception as e:
            logger.error(f"Failed to update sync status: {e}")

    def _check_online_status(self) -> None:
        """Check online connectivity status."""
        try:
            # Simple connectivity check - in real implementation would ping server
            import socket
            socket.setdefaulttimeout(3)

            # Try to connect to sync server host
            if sync_settings.sync_enabled:
                host = str(sync_settings.sync_api_url).split("://")[1].split("/")[0].split(":")[0]
                socket.create_connection((host, 80), timeout=3)
                new_online = True
            else:
                new_online = False

        except Exception:
            new_online = False

        if new_online != self._is_online:
            self._is_online = new_online
            self.isOnlineChanged.emit(self._is_online)
            logger.debug(f"Online status changed: {self._is_online}")

    def on_sync_started(self) -> None:
        """Handle sync engine started event."""
        self._sync_progress = 0.0
        self.syncProgressChanged.emit(self._sync_progress)
        self._is_syncing = True
        self.isSyncingChanged.emit(self._is_syncing)
        self.syncStarted.emit()
        logger.debug("Sync started")

    def on_sync_progress(self, progress: float) -> None:
        """Handle sync progress update."""
        self._sync_progress = max(0.0, min(1.0, progress))
        self.syncProgressChanged.emit(self._sync_progress)

    def on_sync_completed(self, changes_count: int) -> None:
        """Handle sync engine completed event."""
        self._sync_progress = 1.0
        self.syncProgressChanged.emit(self._sync_progress)

        # Update last sync time
        self._last_sync_time = QDateTime.currentDateTime()
        self.lastSyncTimeChanged.emit(self._last_sync_time)

        # Update pending count
        self._update_status()

        self._is_syncing = False
        self.isSyncingChanged.emit(self._is_syncing)
        self.syncCompleted.emit(changes_count)
        logger.info(f"Sync completed: {changes_count} changes")

    def on_sync_failed(self, error_message: str) -> None:
        """Handle sync engine failed event."""
        self._sync_progress = 0.0
        self.syncProgressChanged.emit(self._sync_progress)
        self._is_syncing = False
        self.isSyncingChanged.emit(self._is_syncing)
        self.syncFailed.emit(error_message)
        logger.warning(f"Sync failed: {error_message}")

    def connectToSyncEngine(self, sync_engine: Any) -> None:
        """Connect to sync engine signals (if available)."""
        # This would connect to actual sync engine signals
        # For now, it's a placeholder for future integration
        logger.info("SyncStatusController connected to sync engine")
