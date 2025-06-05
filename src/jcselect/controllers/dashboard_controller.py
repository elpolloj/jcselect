"""Dashboard controller for navigation and state management."""
from __future__ import annotations

from loguru import logger
from PySide6.QtCore import Property, QDateTime, QObject, QTimer, Signal, Slot
from sqlmodel import func, select

from jcselect.models.tally_session import TallySession
from jcselect.models.voter import Voter
from jcselect.utils.db import get_session
from jcselect.utils.settings import sync_settings


class DashboardController(QObject):
    """Main dashboard controller for navigation and state management."""

    # Signals
    navigationRequested = Signal(str)  # screen_name
    userSwitchRequested = Signal()
    dataUpdated = Signal()
    penChanged = Signal()
    syncStatusChanged = Signal()
    pulseRequested = Signal()  # Signal for pulse animation
    
    # New signals from spec
    connectivityChanged = Signal()
    auditStatusChanged = Signal()
    dataRefreshed = Signal()
    refreshStateChanged = Signal()
    errorOccurred = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize dashboard controller."""
        super().__init__(parent)
        
        # Existing properties
        self._pending_voters = 0
        self._active_sessions = 0
        self._total_voters = 0
        self._current_pen_label = ""
        self._sync_status = "offline"
        self._last_sync_time = QDateTime.currentDateTime()
        self._has_new_results = False
        
        # New properties from spec
        self._is_online = False
        self._is_syncing = False
        self._has_unread_audit_logs = False
        self._total_voters_registered = 0
        self._total_voters_voted = 0
        self._active_tally_sessions = 0
        self._pending_sync_operations = 0
        self._is_refreshing = False
        self._error_message = ""

        # Enhanced polling timer
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(sync_settings.dashboard_poll_secs * 1000)
        self._poll_timer.timeout.connect(self.refreshDashboardData)
        self._poll_timer.start()

        # Connect to sync status controller for online/offline handling
        self._connect_sync_signals()

        # Initial data load
        self.refreshDashboardData()

    def _connect_sync_signals(self) -> None:
        """Connect to sync engine and status controller signals."""
        try:
            from jcselect.sync.engine import get_sync_engine

            sync_engine = get_sync_engine()
            if sync_engine:
                # Connect to sync completion signal if available
                if hasattr(sync_engine, 'syncCompleted'):
                    sync_engine.syncCompleted.connect(self._on_sync_completed)
                    logger.debug("Connected to sync engine completion signals")
                    
                # Connect to online status changes
                if hasattr(sync_engine, 'isOnlineChanged'):
                    sync_engine.isOnlineChanged.connect(self._handle_online_changed)
        except Exception as e:
            logger.debug(f"Could not connect to sync engine: {e}")

        # Try to connect to sync status controller if available
        try:
            from jcselect.controllers.sync_status_controller import SyncStatusController
            
            sync_status = SyncStatusController.instance()
            if sync_status:
                sync_status.isOnlineChanged.connect(self._handle_online_changed)
                logger.debug("Connected to sync status controller")
        except Exception as e:
            logger.debug(f"Could not connect to sync status controller: {e}")

    @Slot(bool)
    def _handle_online_changed(self, online: bool) -> None:
        """Handle online/offline status changes."""
        self._is_online = online
        self.connectivityChanged.emit()
        
        # Pause/resume polling timer based on online status
        if online:
            if not self._poll_timer.isActive():
                self._poll_timer.start()
                logger.debug("Dashboard polling resumed (online)")
                # Update immediately when coming back online
                self.refreshDashboardData()
        else:
            if self._poll_timer.isActive():
                self._poll_timer.stop()
                logger.debug("Dashboard polling paused (offline)")

    @Slot()
    def _on_sync_completed(self) -> None:
        """Handle sync completion to update dashboard data."""
        logger.debug("Sync completed - updating dashboard data")
        self.refreshDashboardData()
        self.updateSyncStatus("online")

    # Status Properties
    def _get_is_online(self) -> bool:
        """Get online status."""
        return self._is_online

    isOnline = Property(bool, _get_is_online, notify=connectivityChanged)  # type: ignore[call-arg,arg-type]

    def _get_is_syncing(self) -> bool:
        """Get syncing status."""
        return self._is_syncing

    isSyncing = Property(bool, _get_is_syncing, notify=syncStatusChanged)  # type: ignore[call-arg,arg-type]

    def _get_last_sync_time(self) -> QDateTime:
        """Get last sync time."""
        return self._last_sync_time

    lastSyncTime = Property("QDateTime", _get_last_sync_time, notify=syncStatusChanged)  # type: ignore[call-arg,arg-type]

    def _get_has_unread_audit_logs(self) -> bool:
        """Get unread audit logs status."""
        return self._has_unread_audit_logs

    hasUnreadAuditLogs = Property(bool, _get_has_unread_audit_logs, notify=auditStatusChanged)  # type: ignore[call-arg,arg-type]

    # Live Data Properties
    def _get_total_voters_registered(self) -> int:
        """Get total registered voters."""
        return self._total_voters_registered

    totalVotersRegistered = Property(int, _get_total_voters_registered, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_total_voters_voted(self) -> int:
        """Get total voters who voted."""
        return self._total_voters_voted

    totalVotersVoted = Property(int, _get_total_voters_voted, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_active_tally_sessions(self) -> int:
        """Get active tally sessions count."""
        return self._active_tally_sessions

    activeTallySessions = Property(int, _get_active_tally_sessions, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_pending_sync_operations(self) -> int:
        """Get pending sync operations count."""
        return self._pending_sync_operations

    pendingSyncOperations = Property(int, _get_pending_sync_operations, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    # UI State Properties
    def _get_is_refreshing(self) -> bool:
        """Get refreshing state."""
        return self._is_refreshing

    isRefreshing = Property(bool, _get_is_refreshing, notify=refreshStateChanged)  # type: ignore[call-arg,arg-type]

    def _get_error_message(self) -> str:
        """Get error message."""
        return self._error_message

    errorMessage = Property(str, _get_error_message, notify=errorOccurred)  # type: ignore[call-arg,arg-type]

    # Legacy Properties (for backward compatibility)
    def _get_pending_voters(self) -> int:
        """Get pending voters count."""
        return self._pending_voters

    def _set_pending_voters(self, value: int) -> None:
        """Set pending voters count."""
        self._pending_voters = value

    pendingVoters = Property(int, _get_pending_voters, _set_pending_voters, notify=dataUpdated)  # type: ignore[call-arg,arg-type]

    def _get_active_sessions(self) -> int:
        """Get active sessions count."""
        return self._active_sessions

    def _set_active_sessions(self, value: int) -> None:
        """Set active sessions count."""
        self._active_sessions = value

    activeSessions = Property(int, _get_active_sessions, _set_active_sessions, notify=dataUpdated)  # type: ignore[call-arg,arg-type]

    def _get_total_voters(self) -> int:
        """Get total voters count."""
        return self._total_voters

    def _set_total_voters(self, value: int) -> None:
        """Set total voters count."""
        self._total_voters = value

    totalVoters = Property(int, _get_total_voters, _set_total_voters, notify=dataUpdated)  # type: ignore[call-arg,arg-type]

    def _get_current_pen_label(self) -> str:
        """Get current pen label."""
        return self._current_pen_label

    def _set_current_pen_label(self, value: str) -> None:
        """Set current pen label."""
        self._current_pen_label = value

    currentPenLabel = Property(str, _get_current_pen_label, _set_current_pen_label, notify=penChanged)  # type: ignore[call-arg,arg-type]

    def _get_sync_status(self) -> str:
        """Get sync status."""
        return self._sync_status

    def _set_sync_status(self, value: str) -> None:
        """Set sync status."""
        self._sync_status = value

    syncStatus = Property(str, _get_sync_status, _set_sync_status, notify=syncStatusChanged)  # type: ignore[call-arg,arg-type]

    def _get_has_new_results(self) -> bool:
        """Get hasNewResults flag."""
        return self._has_new_results

    def _set_has_new_results(self, value: bool) -> None:
        """Set hasNewResults flag."""
        self._has_new_results = value

    hasNewResults = Property(bool, _get_has_new_results, _set_has_new_results, notify=dataUpdated)  # type: ignore[call-arg,arg-type]

    @Slot()
    def refreshDashboardData(self) -> None:
        """Refresh all dashboard statistics (public slot)."""
        if self._is_refreshing:
            return  # Prevent multiple concurrent refreshes
            
        self._is_refreshing = True
        self.refreshStateChanged.emit()
        
        # Use QTimer.singleShot for non-blocking execution
        def _do_refresh():
            try:
                with get_session() as session:
                    # Get voter statistics with optimized queries
                    total_voters_query = select(func.count(Voter.id)).select_from(Voter)  # type: ignore[arg-type]
                    if hasattr(Voter, 'deleted_at'):
                        total_voters_query = total_voters_query.where(Voter.deleted_at.is_(None))  # type: ignore[union-attr]
                    
                    voted_query = select(func.count(Voter.id)).select_from(Voter).where(  # type: ignore[arg-type]
                        Voter.has_voted == True  # noqa: E712
                    )
                    if hasattr(Voter, 'deleted_at'):
                        voted_query = voted_query.where(Voter.deleted_at.is_(None))  # type: ignore[union-attr]

                    # Count pending voters (not voted, not deleted)
                    pending_query = select(func.count(Voter.id)).select_from(Voter).where(  # type: ignore[arg-type]
                        Voter.has_voted == False  # noqa: E712
                    )
                    if hasattr(Voter, 'deleted_at'):
                        pending_query = pending_query.where(Voter.deleted_at.is_(None))  # type: ignore[union-attr]

                    # Count active tally sessions (not completed, not deleted)
                    sessions_query = select(func.count(TallySession.id)).select_from(TallySession).where(  # type: ignore[arg-type]
                        TallySession.completed_at.is_(None)  # type: ignore[union-attr]
                    )
                    if hasattr(TallySession, 'deleted_at'):
                        sessions_query = sessions_query.where(TallySession.deleted_at.is_(None))  # type: ignore[union-attr]

                    # Execute queries efficiently
                    self._total_voters_registered = session.exec(total_voters_query).first() or 0
                    self._total_voters_voted = session.exec(voted_query).first() or 0
                    self._pending_voters = session.exec(pending_query).first() or 0
                    self._active_tally_sessions = session.exec(sessions_query).first() or 0

                    # Legacy properties for backward compatibility
                    self._active_sessions = self._active_tally_sessions
                    self._total_voters = self._total_voters_registered

                # Get sync status (non-blocking)
                try:
                    from jcselect.sync.engine import get_sync_engine
                    sync_engine = get_sync_engine()
                    if sync_engine:
                        self._pending_sync_operations = getattr(sync_engine, 'pending_operations_count', lambda: 0)()
                        self._is_syncing = getattr(sync_engine, 'is_active', lambda: False)()
                    else:
                        self._pending_sync_operations = 0
                        self._is_syncing = False
                except Exception as e:
                    logger.debug(f"Could not get sync status: {e}")
                    self._pending_sync_operations = 0
                    self._is_syncing = False

                # Clear any existing error
                self._error_message = ""
                
                # Emit signals
                self.dataRefreshed.emit()
                self.dataUpdated.emit()  # Legacy signal
                
                logger.debug(f"Dashboard data refreshed: {self._total_voters_registered} voters, "
                            f"{self._total_voters_voted} voted, {self._active_tally_sessions} active sessions")

            except Exception as e:
                self._error_message = f"Failed to refresh data: {str(e)}"
                self.errorOccurred.emit()
                logger.error(f"Dashboard data refresh failed: {e}")
                
            finally:
                self._is_refreshing = False
                self.refreshStateChanged.emit()
        
        # Execute refresh with a small delay to avoid blocking UI
        QTimer.singleShot(50, _do_refresh)

    @Slot()
    def checkConnectivity(self) -> None:
        """Check connectivity status."""
        try:
            from jcselect.sync.engine import get_sync_engine
            sync_engine = get_sync_engine()
            if sync_engine:
                self._is_online = getattr(sync_engine, 'is_online', lambda: False)()
            else:
                self._is_online = False
        except Exception:
            self._is_online = False
        
        self.connectivityChanged.emit()

    @Slot()
    def clearError(self) -> None:
        """Clear error message."""
        self._error_message = ""
        self.errorOccurred.emit()

    # Legacy method (for backward compatibility)
    @Slot()
    def updateDashboardData(self) -> None:
        """Update dashboard statistics (legacy method)."""
        self.refreshDashboardData()

    def _pulse_counters(self) -> None:
        """Trigger pulse animation for counters that changed."""
        self.pulseRequested.emit()

    @Slot(str)
    def setPenLabel(self, pen_label: str) -> None:
        """Set current pen label."""
        if self._current_pen_label != pen_label:
            self._current_pen_label = pen_label
            self.penChanged.emit()
            logger.debug(f"Pen changed to: {pen_label}")

    @Slot(str)
    def updateSyncStatus(self, status: str, last_sync: QDateTime | None = None) -> None:
        """Update sync status."""
        self._sync_status = status
        if last_sync:
            self._last_sync_time = last_sync
        else:
            self._last_sync_time = QDateTime.currentDateTime()
        self.syncStatusChanged.emit()
        logger.debug(f"Sync status updated: {status}")

    # Navigation methods
    @Slot()
    def openVoterSearch(self) -> None:
        """Open voter search window."""
        self.navigationRequested.emit("voter_search")

    @Slot()
    def openTallyCounting(self) -> None:
        """Open tally counting window."""
        self.navigationRequested.emit("tally_counting")

    @Slot()
    def openTurnoutReports(self) -> None:
        """Open turnout reports window."""
        self.navigationRequested.emit("turnout_reports")

    @Slot()
    def openResultsCharts(self) -> None:
        """Open results charts window."""
        self.navigationRequested.emit("results_charts")

    @Slot()
    def openWinners(self) -> None:
        """Open winners window."""
        self.navigationRequested.emit("winners")

    @Slot()
    def openLiveResults(self) -> None:
        """Open live results window."""
        self._has_new_results = False  # Clear the new results flag
        self.dataUpdated.emit()
        self.navigationRequested.emit("live_results")

    @Slot()
    def openCountOperations(self) -> None:
        """Open count operations window."""
        self.navigationRequested.emit("count_operations")

    @Slot()
    def openSetup(self) -> None:
        """Open setup window."""
        self.navigationRequested.emit("setup")

    @Slot()
    def openSystemSettings(self) -> None:
        """Open system settings window."""
        self.navigationRequested.emit("system_settings")

    @Slot()
    def openSyncStatus(self) -> None:
        """Open sync status window."""
        self.navigationRequested.emit("sync_status")

    @Slot()
    def openAuditLogs(self) -> None:
        """Open audit logs window."""
        self._has_unread_audit_logs = False  # Clear unread flag
        self.auditStatusChanged.emit()
        self.navigationRequested.emit("audit_logs")

    @Slot()
    def openUserManagement(self) -> None:
        """Open user management window."""
        self.navigationRequested.emit("user_management")

    @Slot()
    def openSettings(self) -> None:
        """Open settings window."""
        self.navigationRequested.emit("settings")

    @Slot()
    def switchUser(self) -> None:
        """Switch user."""
        self.userSwitchRequested.emit()

    @Slot()
    def logout(self) -> None:
        """Logout user."""
        self.navigationRequested.emit("logout")

    @Slot()
    def showAbout(self) -> None:
        """Show about dialog."""
        self.navigationRequested.emit("about")

    def __del__(self) -> None:
        """Clean up timer when controller is destroyed."""
        try:
            if hasattr(self, '_poll_timer') and self._poll_timer is not None:
                self._poll_timer.stop()
                self._poll_timer.deleteLater()
        except (RuntimeError, AttributeError):
            # Timer might already be deleted by Qt
            pass
