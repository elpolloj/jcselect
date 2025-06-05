"""TallyController for ballot counting operations."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger
from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlmodel import select

from jcselect.dao import (
    get_candidates_by_party,
    get_or_create_tally_session,
    get_parties_for_pen,
    get_tally_session_counts,
    tally_line_to_dict,
)
from jcselect.models import BallotType, TallyLine, TallySession
from jcselect.models.sync_schemas import ChangeOperation
from jcselect.sync.queue import sync_queue
from jcselect.utils.db import get_session


class TallyController(QObject):
    """Main tally counting controller for ballot processing."""

    # Signals
    sessionChanged = Signal()
    countsChanged = Signal()
    ballotNumberChanged = Signal()
    partiesLoaded = Signal()
    selectionChanged = Signal()
    ballotTypeChanged = Signal()
    validationChanged = Signal()
    ballotConfirmed = Signal(int)  # ballot_number
    recountStarted = Signal()
    recountCompleted = Signal()
    errorOccurred = Signal(str)

    def __init__(self, parent=None):
        """Initialize TallyController."""
        super().__init__(parent)

        # Internal state
        self._current_session: TallySession | None = None
        self._current_pen_id: UUID | None = None
        self._current_operator_id: UUID | None = None
        self._selected_candidates: dict[str, str] = {}  # party_id -> candidate_id
        self._selected_ballot_type: BallotType = BallotType.NORMAL
        self._party_columns: list[dict[str, Any]] = []
        self._validation_messages: list[str] = []
        self._counts: dict[str, int] = {
            "total_votes": 0,
            "total_counted": 0,
            "total_candidates": 0,
            "total_white": 0,
            "total_illegal": 0,
            "total_cancel": 0,
            "total_blank": 0,
        }

        logger.debug("TallyController initialized")

    # Properties
    @Property('QVariant', notify=sessionChanged)
    def currentSession(self) -> dict[str, Any] | None:
        """Get current tally session info."""
        if not self._current_session:
            return None

        return {
            "id": str(self._current_session.id),
            "session_name": self._current_session.session_name,
            "ballot_number": self._current_session.ballot_number,
            "started_at": self._current_session.started_at.isoformat(),
            "pen_label": getattr(self._current_session, "pen_label", ""),
        }

    @Property(int, notify=countsChanged)
    def totalVotes(self) -> int:
        """Total number of votes counted."""
        return self._counts["total_votes"]

    @Property(int, notify=countsChanged)
    def totalCounted(self) -> int:
        """Total ballots processed."""
        return self._counts["total_counted"]

    @Property(int, notify=countsChanged)
    def totalWhite(self) -> int:
        """Total white ballots."""
        return self._counts["total_white"]

    @Property(int, notify=countsChanged)
    def totalIllegal(self) -> int:
        """Total illegal ballots."""
        return self._counts["total_illegal"]

    @Property(int, notify=countsChanged)
    def totalCandidates(self) -> int:
        """Total candidate votes."""
        return self._counts["total_candidates"]

    @Property(int, notify=countsChanged)
    def totalCancel(self) -> int:
        """Total cancelled ballots."""
        return self._counts["total_cancel"]

    @Property(int, notify=countsChanged)
    def totalBlank(self) -> int:
        """Total blank ballots."""
        return self._counts["total_blank"]

    @Property(int, notify=ballotNumberChanged)
    def currentBallotNumber(self) -> int:
        """Current ballot number being processed."""
        if self._current_session:
            return self._current_session.ballot_number
        return 0

    @Property('QVariantList', notify=partiesLoaded)
    def partyColumns(self) -> list[dict[str, Any]]:
        """Party data for UI columns."""
        return self._party_columns

    @Property('QVariantMap', notify=selectionChanged)
    def selectedCandidates(self) -> dict[str, str]:
        """Currently selected candidates by party."""
        return self._selected_candidates

    @Property(str, notify=ballotTypeChanged)
    def selectedBallotType(self) -> str:
        """Currently selected ballot type."""
        return self._selected_ballot_type.value

    @Property(bool, notify=validationChanged)
    def hasValidationWarnings(self) -> bool:
        """Whether there are validation warnings."""
        return len(self._validation_messages) > 0

    @Property('QStringList', notify=validationChanged)
    def validationMessages(self) -> list[str]:
        """Current validation warning messages."""
        return self._validation_messages

    @Property(str, notify=sessionChanged)
    def currentPenLabel(self) -> str:
        """Current pen label for display."""
        if self._current_session:
            return getattr(self._current_session, "pen_label", "Unknown Pen")
        return ""

    @Property(bool, notify=selectionChanged)
    def hasSelections(self) -> bool:
        """Whether any selections have been made."""
        has_candidates = any(candidate for candidate in self._selected_candidates.values())
        has_special_ballot = self._selected_ballot_type != BallotType.NORMAL
        return has_candidates or has_special_ballot

    # Core Operations
    @Slot(str, str, str)
    def initializeSession(self, pen_id: str, operator_id: str, pen_label: str = ""):
        """Initialize or load tally session for a pen."""
        try:
            self._current_pen_id = UUID(pen_id)
            self._current_operator_id = UUID(operator_id)

            with get_session() as session:
                # Get or create tally session
                self._current_session = get_or_create_tally_session(
                    self._current_pen_id, self._current_operator_id, session
                )

                # Set pen label for display
                if pen_label:
                    self._current_session.pen_label = pen_label

                session.commit()

            # Load party data and refresh counts
            self.loadPartyData()
            self.refreshCounts()

            logger.info(f"Initialized tally session for pen {pen_id}")
            self.sessionChanged.emit()

        except Exception as e:
            error_msg = f"Failed to initialize session: {str(e)}"
            logger.error(error_msg)
            self.errorOccurred.emit(error_msg)

    @Slot(str, str)
    def selectCandidate(self, party_id: str, candidate_id: str):
        """Select a candidate for a party (single selection per party)."""
        # Clear other selections for this party (single selection rule)
        if candidate_id:
            self._selected_candidates[party_id] = candidate_id
        else:
            # Deselect
            self._selected_candidates.pop(party_id, None)

        # Clear special ballot type if selecting candidates
        if any(self._selected_candidates.values()):
            self._selected_ballot_type = BallotType.NORMAL
            self.ballotTypeChanged.emit()

        self._validate_current_ballot()
        self.selectionChanged.emit()

        logger.debug(f"Selected candidate {candidate_id} for party {party_id}")

    @Slot(str)
    def selectBallotType(self, ballot_type: str):
        """Select a ballot type (mutually exclusive with candidate selections)."""
        try:
            self._selected_ballot_type = BallotType(ballot_type)

            # Clear candidate selections if selecting special ballot type
            if self._selected_ballot_type != BallotType.NORMAL:
                self._selected_candidates.clear()
                self.selectionChanged.emit()

            self._validate_current_ballot()
            self.ballotTypeChanged.emit()

            logger.debug(f"Selected ballot type: {ballot_type}")

        except ValueError:
            error_msg = f"Invalid ballot type: {ballot_type}"
            logger.error(error_msg)
            self.errorOccurred.emit(error_msg)

    @Slot()
    def confirmBallot(self):
        """Confirm current ballot and create TallyLine records."""
        if not self._current_session:
            self.errorOccurred.emit("No active tally session")
            return

        try:
            self._confirm_ballot_and_sync()

            # Clear selections for next ballot
            self.clearCurrentBallot()

        except Exception as e:
            error_msg = f"Failed to confirm ballot: {str(e)}"
            logger.error(error_msg)
            self.errorOccurred.emit(error_msg)

    @Slot()
    def clearCurrentBallot(self):
        """Clear current ballot selections."""
        self._selected_candidates.clear()
        self._selected_ballot_type = BallotType.NORMAL
        self._validation_messages.clear()

        self.selectionChanged.emit()
        self.ballotTypeChanged.emit()
        self.validationChanged.emit()

        logger.debug("Cleared current ballot selections")

    @Slot()
    def startRecount(self):
        """Start recount by soft-deleting existing tally lines."""
        if not self._current_session:
            self.errorOccurred.emit("No active tally session")
            return

        try:
            self.recountStarted.emit()

            with get_session() as session:
                # Mark all existing lines as deleted
                existing_lines = session.exec(
                    select(TallyLine).where(
                        TallyLine.tally_session_id == self._current_session.id,
                        TallyLine.deleted_at == None
                    )
                ).all()

                changes_to_sync = []
                now = datetime.utcnow()

                for line in existing_lines:
                    line.deleted_at = now
                    line.deleted_by = self._current_operator_id

                    changes_to_sync.append({
                        "entity_type": "TallyLine",
                        "entity_id": str(line.id),
                        "operation": "UPDATE",
                        "data": tally_line_to_dict(line)
                    })

                # Reset session ballot number
                self._current_session.ballot_number = 0
                self._current_session.recounted_at = now
                self._current_session.recount_operator_id = self._current_operator_id

                session.add(self._current_session)
                session.commit()

                # Queue sync changes using new helper method
                for line in existing_lines:
                    sync_queue.enqueue_tally_line(line, ChangeOperation.UPDATE)

                # Trigger fast sync for immediate updates
                sync_queue.trigger_fast_sync()

            self.recountCompleted.emit()
            self.refreshCounts()
            self.ballotNumberChanged.emit()

            logger.info(f"Recount completed for session {self._current_session.id}")

        except Exception as e:
            error_msg = f"Recount failed: {str(e)}"
            logger.error(error_msg)
            self.errorOccurred.emit(error_msg)

    @Slot()
    def loadPartyData(self):
        """Load party and candidate data for the current pen."""
        if not self._current_pen_id:
            return

        try:
            with get_session() as session:
                parties = get_parties_for_pen(self._current_pen_id, session)

                self._party_columns = []
                for party in parties:
                    candidates = get_candidates_by_party(party.id, session)

                    party_data = {
                        "id": str(party.id),
                        "name": party.name,
                        "abbreviation": party.abbreviation,
                        "candidates": candidates
                    }
                    self._party_columns.append(party_data)

            self.partiesLoaded.emit()
            logger.debug(f"Loaded {len(self._party_columns)} parties")

        except Exception as e:
            error_msg = f"Failed to load party data: {str(e)}"
            logger.error(error_msg)
            self.errorOccurred.emit(error_msg)

    @Slot()
    def refreshCounts(self):
        """Refresh running totals from database."""
        if not self._current_session:
            return

        try:
            with get_session() as session:
                self._counts = get_tally_session_counts(self._current_session.id, session)

            self.countsChanged.emit()
            logger.debug(f"Refreshed counts: {self._counts}")

        except Exception as e:
            error_msg = f"Failed to refresh counts: {str(e)}"
            logger.error(error_msg)
            self.errorOccurred.emit(error_msg)

    # Private helper methods
    def _validate_current_ballot(self) -> list[str]:
        """Validate current ballot selections and return warnings."""
        warnings = []

        # Over-vote detection
        total_selections = len([c for c in self._selected_candidates.values() if c])
        if total_selections > 3:  # Lebanese election rules
            warnings.append("تحذير: عدد الأصوات أكثر من المسموح")

        # Under-vote notification
        if total_selections == 0 and self._selected_ballot_type == BallotType.NORMAL:
            warnings.append("ملاحظة: لم يتم اختيار أي مرشح")

        # Mixed ballot type warnings
        if total_selections > 0 and self._selected_ballot_type != BallotType.NORMAL:
            warnings.append("تحذير: اختيار مرشحين مع نوع ورقة خاص")

        self._validation_messages = warnings
        self.validationChanged.emit()

        return warnings

    def _confirm_ballot_and_sync(self):
        """Confirm ballot and immediately queue for sync."""
        with get_session() as session:
            # Update ballot number
            self._current_session.ballot_number += 1
            session.add(self._current_session)

            # Create TallyLine entries for each selection
            changes_to_sync = []

            for party_id, candidate_id in self._selected_candidates.items():
                if candidate_id:  # Skip empty selections
                    tally_line = TallyLine(
                        tally_session_id=self._current_session.id,
                        party_id=UUID(party_id),
                        vote_count=1,  # Each ballot contributes 1 vote
                        ballot_type=self._selected_ballot_type,
                        ballot_number=self._current_session.ballot_number
                    )
                    session.add(tally_line)
                    session.flush()  # Get the ID

                    # Queue for sync
                    changes_to_sync.append({
                        "entity_type": "TallyLine",
                        "entity_id": str(tally_line.id),
                        "operation": "CREATE",
                        "data": tally_line_to_dict(tally_line)
                    })

            # Handle special ballot types (no party association)
            if self._selected_ballot_type != BallotType.NORMAL:
                # Create a special TallyLine without party_id for counting
                # Note: Current schema requires party_id, so we'll use the first party as placeholder
                # This is a limitation that should be addressed in future schema updates
                if self._party_columns:
                    placeholder_party_id = UUID(self._party_columns[0]["id"])
                    special_line = TallyLine(
                        tally_session_id=self._current_session.id,
                        party_id=placeholder_party_id,  # Placeholder due to schema constraint
                        vote_count=1,
                        ballot_type=self._selected_ballot_type,
                        ballot_number=self._current_session.ballot_number
                    )
                    session.add(special_line)
                    session.flush()

                    changes_to_sync.append({
                        "entity_type": "TallyLine",
                        "entity_id": str(special_line.id),
                        "operation": "CREATE",
                        "data": tally_line_to_dict(special_line)
                    })

            session.commit()

            # Queue all changes for sync using new helper method
            for party_id, candidate_id in self._selected_candidates.items():
                if candidate_id:  # Skip empty selections
                    tally_line = session.exec(
                        select(TallyLine).where(
                            TallyLine.tally_session_id == self._current_session.id,
                            TallyLine.party_id == UUID(party_id),
                            TallyLine.ballot_number == self._current_session.ballot_number
                        )
                    ).first()

                    if tally_line:
                        sync_queue.enqueue_tally_line(tally_line, ChangeOperation.CREATE)

            # Handle special ballot type sync
            if self._selected_ballot_type != BallotType.NORMAL:
                special_lines = session.exec(
                    select(TallyLine).where(
                        TallyLine.tally_session_id == self._current_session.id,
                        TallyLine.ballot_type == self._selected_ballot_type,
                        TallyLine.ballot_number == self._current_session.ballot_number
                    )
                ).all()

                for line in special_lines:
                    sync_queue.enqueue_tally_line(line, ChangeOperation.CREATE)

            # Trigger fast sync for immediate badge updates
            sync_queue.trigger_fast_sync()

            # Update dashboard badges immediately
            self.ballotConfirmed.emit(self._current_session.ballot_number)
            self.ballotNumberChanged.emit()
            self._refresh_counts()

    def _refresh_counts(self):
        """Internal method to refresh counts without error handling."""
        if self._current_session:
            with get_session() as session:
                self._counts = get_tally_session_counts(self._current_session.id, session)
            self.countsChanged.emit()
