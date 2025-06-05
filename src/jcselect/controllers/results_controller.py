"""Results controller for live results and winner calculation."""
from __future__ import annotations

from typing import Any

from loguru import logger
from PySide6.QtCore import Property, QDateTime, QObject, QTimer, Signal, Slot
from sqlmodel import select

from jcselect.dao_results import (
    calculate_winners,
    get_pen_completion_status,
    get_pen_voter_turnout,
    get_totals_by_candidate,
    get_totals_by_party,
)
from jcselect.models import Pen
from jcselect.utils.db import get_session


class ResultsController(QObject):
    """Controller for live results and winner calculation."""

    # Data update signals
    dataRefreshed = Signal()
    winnersCalculated = Signal()
    pensLoaded = Signal()

    # UI interaction signals
    penFilterChanged = Signal()
    partyFilterChanged = Signal()
    syncStatusChanged = Signal()

    # Export signals
    exportCompleted = Signal(str)  # file_path
    exportFailed = Signal(str)     # error_message

    # Error handling
    errorOccurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize results controller."""
        super().__init__(parent)

        # Private data properties
        self._party_totals: list[dict[str, Any]] = []
        self._candidate_totals: list[dict[str, Any]] = []
        self._winners: list[dict[str, Any]] = []

        # Private UI state properties
        self._selected_pen_id = ""
        self._available_pens: list[dict[str, Any]] = []
        self._last_updated = QDateTime.currentDateTime()
        self._is_syncing = False
        self._total_ballots = 0
        self._completion_percent = 0.0

        # Private filter properties
        self._show_all_pens = True
        self._selected_party_id = ""
        self._candidate_filter = ""

        # New results notification
        self._has_new_results = False
        self._new_results_timer = QTimer()
        self._new_results_timer.setSingleShot(True)
        self._new_results_timer.timeout.connect(self._clear_new_results_flag)

        # Auto-refresh timer for debouncing sync events
        self._refresh_timer = QTimer()
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refreshData)

        # Auto-refresh control
        self._auto_refresh_enabled = True

        # Connect to sync engine
        self._connect_sync_signals()

        # Initial data load
        QTimer.singleShot(100, self.loadAvailablePens)
        QTimer.singleShot(200, self.refreshData)

    def _clear_new_results_flag(self) -> None:
        """Clear the hasNewResults flag after 3 seconds."""
        self._has_new_results = False

    def _connect_sync_signals(self) -> None:
        """Connect to sync engine signals for auto-refresh."""
        try:
            from jcselect.sync.engine import get_sync_engine

            sync_engine = get_sync_engine()
            if sync_engine:
                # Connect to sync completion signals if available
                if hasattr(sync_engine, 'syncCompleted'):
                    sync_engine.syncCompleted.connect(self._on_sync_completed)
                if hasattr(sync_engine, 'tallyLineUpdated'):
                    sync_engine.tallyLineUpdated.connect(self._on_tally_updated)
                logger.debug("Connected to sync engine signals")
        except Exception as e:
            logger.debug(f"Could not connect to sync engine: {e}")

    @Slot()
    def _on_sync_completed(self) -> None:
        """Handle sync completion with debounced refresh."""
        logger.debug("Sync completed - scheduling results refresh")
        self._is_syncing = False
        self.syncStatusChanged.emit()
        # Set new results flag for 3 seconds
        self._has_new_results = True
        self._new_results_timer.start(3000)
        # Debounce refresh by 250ms as specified
        self._refresh_timer.start(250)

    @Slot(str)
    def _on_tally_updated(self, tally_line_id: str) -> None:
        """Handle specific tally line updates."""
        logger.debug(f"Tally line updated: {tally_line_id}")
        self._is_syncing = True
        self.syncStatusChanged.emit()
        # Only refresh if auto-refresh is enabled
        if self._auto_refresh_enabled:
            # Debounce refresh by 250ms
            self._refresh_timer.start(250)

    # Data Properties
    def _get_party_totals(self) -> list[dict[str, Any]]:
        """Get party totals list."""
        return self._party_totals

    def _set_party_totals(self, value: list[dict[str, Any]]) -> None:
        """Set party totals list."""
        self._party_totals = value

    partyTotals = Property('QVariantList', _get_party_totals, _set_party_totals, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_candidate_totals(self) -> list[dict[str, Any]]:
        """Get candidate totals list."""
        return self._candidate_totals

    def _set_candidate_totals(self, value: list[dict[str, Any]]) -> None:
        """Set candidate totals list."""
        self._candidate_totals = value

    candidateTotals = Property('QVariantList', _get_candidate_totals, _set_candidate_totals, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_winners(self) -> list[dict[str, Any]]:
        """Get winners list."""
        return self._winners

    def _set_winners(self, value: list[dict[str, Any]]) -> None:
        """Set winners list."""
        self._winners = value

    winners = Property('QVariantList', _get_winners, _set_winners, notify=winnersCalculated)  # type: ignore[call-arg,arg-type]

    # UI State Properties
    def _get_selected_pen_id(self) -> str:
        """Get selected pen ID."""
        return self._selected_pen_id

    def _set_selected_pen_id(self, value: str) -> None:
        """Set selected pen ID."""
        self._selected_pen_id = value

    selectedPenId = Property(str, _get_selected_pen_id, _set_selected_pen_id, notify=penFilterChanged)  # type: ignore[call-arg,arg-type]

    def _get_available_pens(self) -> list[dict[str, Any]]:
        """Get available pens list."""
        return self._available_pens

    def _set_available_pens(self, value: list[dict[str, Any]]) -> None:
        """Set available pens list."""
        self._available_pens = value

    availablePens = Property('QVariantList', _get_available_pens, _set_available_pens, notify=pensLoaded)  # type: ignore[call-arg,arg-type]

    def _get_last_updated(self) -> QDateTime:
        """Get last updated timestamp."""
        return self._last_updated

    def _set_last_updated(self, value: QDateTime) -> None:
        """Set last updated timestamp."""
        self._last_updated = value

    lastUpdated = Property('QDateTime', _get_last_updated, _set_last_updated, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_is_syncing(self) -> bool:
        """Get syncing status."""
        return self._is_syncing

    def _set_is_syncing(self, value: bool) -> None:
        """Set syncing status."""
        self._is_syncing = value

    isSyncing = Property(bool, _get_is_syncing, _set_is_syncing, notify=syncStatusChanged)  # type: ignore[call-arg,arg-type]

    def _get_total_ballots(self) -> int:
        """Get total ballots count."""
        return self._total_ballots

    def _set_total_ballots(self, value: int) -> None:
        """Set total ballots count."""
        self._total_ballots = value

    totalBallots = Property(int, _get_total_ballots, _set_total_ballots, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_completion_percent(self) -> float:
        """Get completion percentage."""
        return self._completion_percent

    def _set_completion_percent(self, value: float) -> None:
        """Set completion percentage."""
        self._completion_percent = value

    completionPercent = Property(float, _get_completion_percent, _set_completion_percent, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_has_new_results(self) -> bool:
        """Get hasNewResults flag for dashboard badge."""
        return self._has_new_results

    def _set_has_new_results(self, value: bool) -> None:
        """Set hasNewResults flag."""
        self._has_new_results = value

    hasNewResults = Property(bool, _get_has_new_results, _set_has_new_results, notify=dataRefreshed)  # type: ignore[call-arg,arg-type]

    def _get_auto_refresh_enabled(self) -> bool:
        """Get auto-refresh enabled flag."""
        return self._auto_refresh_enabled

    def _set_auto_refresh_enabled(self, value: bool) -> None:
        """Set auto-refresh enabled flag."""
        self._auto_refresh_enabled = value

    autoRefreshEnabled = Property(bool, _get_auto_refresh_enabled, _set_auto_refresh_enabled, notify=syncStatusChanged)  # type: ignore[call-arg,arg-type]

    # Filter Properties
    def _get_show_all_pens(self) -> bool:
        """Get show all pens flag."""
        return self._show_all_pens

    def _set_show_all_pens(self, value: bool) -> None:
        """Set show all pens flag."""
        self._show_all_pens = value

    showAllPens = Property(bool, _get_show_all_pens, _set_show_all_pens, notify=penFilterChanged)  # type: ignore[call-arg,arg-type]

    def _get_selected_party_id(self) -> str:
        """Get selected party ID."""
        return self._selected_party_id

    def _set_selected_party_id(self, value: str) -> None:
        """Set selected party ID."""
        self._selected_party_id = value

    selectedPartyId = Property(str, _get_selected_party_id, _set_selected_party_id, notify=partyFilterChanged)  # type: ignore[call-arg,arg-type]

    # Slots for data management
    @Slot()
    def refreshData(self) -> None:
        """Refresh all results data."""
        try:
            logger.debug("Refreshing results data")

            # Determine pen filter
            pen_filter = None if self._show_all_pens else self._selected_pen_id
            if pen_filter and pen_filter.strip() == "":
                pen_filter = None

            # Get party totals (DAO functions manage their own sessions)
            self._party_totals = get_totals_by_party(pen_filter)

            # Get candidate totals
            self._candidate_totals = get_totals_by_candidate(pen_filter)

            # Calculate total ballots and completion
            self._calculate_statistics()

            # Update timestamp
            self._last_updated = QDateTime.currentDateTime()

            # Emit signals
            self.dataRefreshed.emit()

            logger.debug(f"Refreshed data: {len(self._party_totals)} parties, {len(self._candidate_totals)} candidates")

        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")
            self.errorOccurred.emit(str(e))

    @Slot()
    def refreshNow(self) -> None:
        """Force manual refresh regardless of auto-refresh setting."""
        logger.debug("Manual refresh requested")
        self.refreshData()

    def _calculate_statistics(self) -> None:
        """Calculate total ballots and completion percentage."""
        try:
            total_ballots = 0
            completed_pens = 0
            total_pens = len(self._available_pens)

            if self._show_all_pens:
                # Calculate for all pens
                for pen_data in self._available_pens:
                    pen_id = pen_data.get("id", "")
                    if pen_id:
                        turnout = get_pen_voter_turnout(pen_id)
                        total_ballots += turnout.get("total_ballots", 0)

                        if get_pen_completion_status(pen_id):
                            completed_pens += 1
            else:
                # Calculate for selected pen only
                if self._selected_pen_id:
                    turnout = get_pen_voter_turnout(self._selected_pen_id)
                    total_ballots = turnout.get("total_ballots", 0)
                    completed_pens = 1 if get_pen_completion_status(self._selected_pen_id) else 0
                    total_pens = 1

            self._total_ballots = total_ballots
            self._completion_percent = (completed_pens / total_pens * 100.0) if total_pens > 0 else 0.0

        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            self._total_ballots = 0
            self._completion_percent = 0.0

    @Slot(str)
    def setPenFilter(self, pen_id: str) -> None:
        """Set pen filter and refresh data."""
        if pen_id != self._selected_pen_id:
            self._selected_pen_id = pen_id
            self._show_all_pens = (pen_id == "" or pen_id == "all")
            self.penFilterChanged.emit()
            self.refreshData()

    @Slot(str)
    def setPartyFilter(self, party_id: str) -> None:
        """Set party filter and refresh data."""
        if party_id != self._selected_party_id:
            self._selected_party_id = party_id
            self.partyFilterChanged.emit()
            # TODO: Implement party filtering in DAO functions
            # For now, just emit signal for UI updates

    @Slot(str)
    def setCandidateFilter(self, filter_text: str) -> None:
        """Set candidate filter text (stub implementation)."""
        if filter_text != self._candidate_filter:
            self._candidate_filter = filter_text
            logger.debug(f"Candidate filter set to: {filter_text}")
            # TODO: Implement actual filtering logic in DAO or here
            # For now, just store the filter text for future implementation

    @Slot()
    def loadAvailablePens(self) -> None:
        """Load available pens for the dropdown."""
        try:
            with get_session() as session:
                # Get all pens (with soft-delete support if available)
                stmt = select(Pen)
                if hasattr(Pen, 'deleted_at'):
                    stmt = stmt.where(Pen.deleted_at.is_(None))

                pens = session.exec(stmt).all()

                # Convert to QML-compatible format
                pen_list = []
                for pen in pens:
                    pen_data = {
                        "id": str(pen.id),
                        "label": pen.label,
                        "town_name": pen.town_name,
                        "display_name": f"{pen.town_name} - {pen.label}"
                    }
                    pen_list.append(pen_data)

                # Sort by display name
                pen_list.sort(key=lambda x: x["display_name"])

                self._available_pens = pen_list
                self.pensLoaded.emit()

                logger.debug(f"Loaded {len(pen_list)} available pens")

        except Exception as e:
            logger.error(f"Failed to load available pens: {e}")
            self.errorOccurred.emit(str(e))

    @Slot()
    def calculateWinners(self) -> None:
        """Calculate winners based on current filter."""
        try:
            # Use current pen filter
            pen_filter = None if self._show_all_pens else self._selected_pen_id
            if pen_filter and pen_filter.strip() == "":
                pen_filter = None

            # Calculate winners with default 3 seats (DAO manages its own session)
            self._winners = calculate_winners(pen_filter, 3)
            self.winnersCalculated.emit()

            logger.debug(f"Calculated {len(self._winners)} winner entries")

        except Exception as e:
            logger.error(f"Failed to calculate winners: {e}")
            self.errorOccurred.emit(str(e))

    @Slot()
    def exportCsv(self) -> None:
        """Export current results to CSV using file dialog."""
        try:
            from PySide6.QtWidgets import QFileDialog, QApplication
            from jcselect.utils.export import (
                export_party_totals_csv,
                export_candidate_results_csv, 
                get_export_filename,
                validate_export_path
            )
            
            # Get main window as parent for dialog
            app = QApplication.instance()
            parent = app.activeWindow() if app else None
            
            # Generate default filename
            default_filename = get_export_filename("party_totals", "csv", "results")
            
            # Show file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                "Export Results to CSV",
                default_filename,
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                # User cancelled
                return
                
            # Validate export path
            if not validate_export_path(file_path):
                self.exportFailed.emit("Cannot write to selected location")
                return
                
            # Export party totals first
            if self._party_totals:
                export_party_totals_csv(self._party_totals, file_path)
                self.exportCompleted.emit(file_path)
                logger.info(f"CSV export completed: {file_path}")
            else:
                # Try candidate results if no party totals
                if self._candidate_totals:
                    export_candidate_results_csv(self._candidate_totals, file_path)
                    self.exportCompleted.emit(file_path)
                    logger.info(f"CSV export completed: {file_path}")
                else:
                    self.exportFailed.emit("No data available for export")

        except Exception as e:
            error_msg = f"CSV export failed: {e}"
            logger.error(error_msg)
            self.exportFailed.emit(error_msg)

    @Slot()
    def exportPdf(self) -> None:
        """Export current results to PDF using file dialog."""
        try:
            from PySide6.QtWidgets import QFileDialog, QApplication
            from jcselect.utils.export import (
                export_results_pdf,
                get_export_filename,
                validate_export_path
            )
            
            # Get main window as parent for dialog
            app = QApplication.instance()
            parent = app.activeWindow() if app else None
            
            # Generate default filename
            default_filename = get_export_filename("report", "pdf", "results")
            
            # Show file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                "Export Results to PDF",
                default_filename,
                "PDF Files (*.pdf);;All Files (*)"
            )
            
            if not file_path:
                # User cancelled
                return
                
            # Validate export path
            if not validate_export_path(file_path):
                self.exportFailed.emit("Cannot write to selected location")
                return
                
            # Prepare data for export
            export_data = {
                "party_totals": self._party_totals,
                "candidate_totals": self._candidate_totals,
                "winners": self._winners,
                "metadata": {
                    "exported_at": QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"),
                    "pen_filter": self._selected_pen_id if not self._show_all_pens else "all",
                    "total_ballots": self._total_ballots,
                    "completion_percent": self._completion_percent
                }
            }
            
            # Check if we have any data to export
            has_data = (self._party_totals or self._candidate_totals or self._winners)
            if not has_data:
                self.exportFailed.emit("No data available for export")
                return
            
            # Export to PDF
            export_results_pdf(export_data, file_path)
            self.exportCompleted.emit(file_path)
            logger.info(f"PDF export completed: {file_path}")

        except Exception as e:
            error_msg = f"PDF export failed: {e}"
            logger.error(error_msg)
            self.exportFailed.emit(error_msg)
