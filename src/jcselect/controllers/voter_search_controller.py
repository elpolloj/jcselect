"""Voter search controller for the UI layer."""
from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from loguru import logger
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from sqlalchemy import case, or_
from sqlmodel import Session, col, select

from jcselect.dao import mark_voted, soft_delete_voter
from jcselect.models import User, Voter
from jcselect.models.dto import SearchResultDTO, VoterDTO
from jcselect.utils.db import get_session


class VoterSearchController(QObject):
    """Controller for voter search and marking functionality."""

    # Signals
    searchQueryChanged = Signal()
    selectedVoterChanged = Signal()
    searchResultsChanged = Signal()
    isLoadingChanged = Signal()
    errorMessageChanged = Signal()
    voterMarkedSuccessfully = Signal(str)  # voter name
    voterDeletedSuccessfully = Signal(str)  # voter id
    operationFailed = Signal(str)  # error message
    searchBarFocusRequested = Signal()  # request to focus search bar
    performanceMetricChanged = Signal()  # performance metric updated

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the voter search controller."""
        super().__init__(parent)
        self._search_query = ""
        self._selected_voter: VoterDTO | None = None
        self._search_results: list[VoterDTO] = []
        self._is_loading = False
        self._error_message = ""

        # Performance metrics
        self._last_search_time_ms = 0.0
        self._last_mark_time_ms = 0.0
        self._total_searches = 0
        self._total_marks = 0
        self._avg_search_time_ms = 0.0
        self._avg_mark_time_ms = 0.0

        # Debounce timer for search
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)
        self._debounce_delay_ms = 300

        # Search timeout threshold (200ms)
        self._search_timeout_threshold_ms = 200

        logger.info("VoterSearchController initialized")

    # Properties
    def _get_search_query(self) -> str:
        return self._search_query

    def _set_search_query(self, value: str) -> None:
        if self._search_query != value:
            self._search_query = value
            self.searchQueryChanged.emit()

    searchQuery = Property(str, _get_search_query, _set_search_query)  # type: ignore

    def _get_selected_voter(self) -> Any:
        """Return selected voter as QVariant for QML."""
        if self._selected_voter is None:
            return None
        return {
            "id": self._selected_voter.id,
            "voterNumber": self._selected_voter.voter_number,
            "fullName": self._selected_voter.full_name,
            "fatherName": self._selected_voter.father_name or "",
            "motherName": self._selected_voter.mother_name or "",
            "penLabel": self._selected_voter.pen_label,
            "hasVoted": self._selected_voter.has_voted,
            "votedAt": self._selected_voter.voted_at.isoformat() if self._selected_voter.voted_at else "",
            "votedByOperator": self._selected_voter.voted_by_operator or "",
        }

    def _set_selected_voter(self, voter: VoterDTO | None) -> None:
        if self._selected_voter != voter:
            self._selected_voter = voter
            self.selectedVoterChanged.emit()

    selectedVoter = Property("QVariant", _get_selected_voter, _set_selected_voter)  # type: ignore

    def _get_search_results(self) -> list[dict[str, Any]]:
        """Return search results as QVariantList for QML."""
        return [
            {
                "id": voter.id,
                "voterNumber": voter.voter_number,
                "fullName": voter.full_name,
                "fatherName": voter.father_name or "",
                "motherName": voter.mother_name or "",
                "penLabel": voter.pen_label,
                "hasVoted": voter.has_voted,
                "votedAt": voter.voted_at.isoformat() if voter.voted_at else "",
                "votedByOperator": voter.voted_by_operator or "",
            }
            for voter in self._search_results
        ]

    def _set_search_results(self, results: list[VoterDTO]) -> None:
        if self._search_results != results:
            self._search_results = results
            self.searchResultsChanged.emit()

    searchResults = Property("QVariantList", _get_search_results, _set_search_results)  # type: ignore

    def _get_is_loading(self) -> bool:
        return self._is_loading

    def _set_is_loading(self, value: bool) -> None:
        if self._is_loading != value:
            self._is_loading = value
            self.isLoadingChanged.emit()

    isLoading = Property(bool, _get_is_loading, _set_is_loading)  # type: ignore

    def _get_error_message(self) -> str:
        return self._error_message

    def _set_error_message(self, value: str) -> None:
        if self._error_message != value:
            self._error_message = value
            self.errorMessageChanged.emit()

    errorMessage = Property(str, _get_error_message, _set_error_message)  # type: ignore

    # Performance metric properties
    def _get_last_search_time_ms(self) -> float:
        return self._last_search_time_ms

    def _set_last_search_time_ms(self, value: float) -> None:
        if self._last_search_time_ms != value:
            self._last_search_time_ms = value
            self.performanceMetricChanged.emit()

    lastSearchTimeMs = Property(float, _get_last_search_time_ms, _set_last_search_time_ms)  # type: ignore

    def _get_last_mark_time_ms(self) -> float:
        return self._last_mark_time_ms

    def _set_last_mark_time_ms(self, value: float) -> None:
        if self._last_mark_time_ms != value:
            self._last_mark_time_ms = value
            self.performanceMetricChanged.emit()

    lastMarkTimeMs = Property(float, _get_last_mark_time_ms, _set_last_mark_time_ms)  # type: ignore

    def _get_avg_search_time_ms(self) -> float:
        return self._avg_search_time_ms

    avgSearchTimeMs = Property(float, _get_avg_search_time_ms)  # type: ignore

    def _get_avg_mark_time_ms(self) -> float:
        return self._avg_mark_time_ms

    avgMarkTimeMs = Property(float, _get_avg_mark_time_ms)  # type: ignore

    def _get_total_searches(self) -> int:
        return self._total_searches

    totalSearches = Property(int, _get_total_searches)  # type: ignore

    def _get_total_marks(self) -> int:
        return self._total_marks

    totalMarks = Property(int, _get_total_marks)  # type: ignore

    # Slots
    @Slot(str)
    def setSearchQuery(self, query: str) -> None:
        """Update search query with debouncing and validation."""
        cleaned_query = query.strip()
        self._set_search_query(cleaned_query)
        self._set_error_message("")  # Clear previous errors

        # Stop any existing timer
        self._search_timer.stop()

        if cleaned_query:
            # Validate minimum query length
            if len(cleaned_query) < 1:
                error_msg = QGuiApplication.translate("VoterSearchController", "Enter a search term")
                self._set_error_message(error_msg)
                self.operationFailed.emit(error_msg)
                return

            # Start debounced search
            self._search_timer.start(self._debounce_delay_ms)
        else:
            # Clear results immediately for empty query
            self._set_search_results([])
            self._set_is_loading(False)

    @Slot(str)
    def selectVoter(self, voter_id: str) -> None:
        """Select voter for detailed view with error handling."""
        try:
            self._set_error_message("")  # Clear previous errors

            # Find voter in current search results
            selected = None
            for voter in self._search_results:
                if voter.id == voter_id:
                    selected = voter
                    break

            if selected is None:
                # If not in current results, query database
                try:
                    with get_session() as session:
                        db_voter = session.get(Voter, UUID(voter_id))
                        if db_voter:
                            selected = self._convert_voter_to_dto(db_voter, session)
                        else:
                            error_msg = QGuiApplication.translate("VoterSearchController", "Voter not found")
                            self._set_error_message(error_msg)
                            self.operationFailed.emit(error_msg)
                            return
                except Exception as db_error:
                    error_msg = QGuiApplication.translate("VoterSearchController", "Database connection failed")
                    logger.error(f"Database error in selectVoter: {db_error}")
                    self._set_error_message(error_msg)
                    self.operationFailed.emit(error_msg)
                    return

            self._set_selected_voter(selected)
            logger.debug(f"Selected voter: {voter_id}")

        except ValueError as e:
            error_msg = QGuiApplication.translate("VoterSearchController", "Invalid voter ID")
            logger.warning(f"Validation error in selectVoter: {e}")
            self._set_error_message(error_msg)
            self.operationFailed.emit(error_msg)
        except Exception as e:
            error_msg = QGuiApplication.translate("VoterSearchController", "Failed to load voter details")
            logger.error(f"Unexpected error in selectVoter {voter_id}: {e}")
            self._set_error_message(error_msg)
            self.operationFailed.emit(error_msg)

    @Slot(str, str)
    def markVoterAsVoted(self, voter_id: str, operator_id: str) -> None:
        """Mark voter as voted with comprehensive error handling and performance monitoring."""
        start_time = time.perf_counter()

        try:
            self._set_is_loading(True)
            self._set_error_message("")  # Clear previous errors

            # Validate inputs
            if not voter_id or not operator_id:
                error_msg = QGuiApplication.translate("VoterSearchController", "Missing voter or operator information")
                self._set_error_message(error_msg)
                self.operationFailed.emit(error_msg)
                return

            # Check if voter is already voted (pre-check)
            if self._selected_voter and self._selected_voter.has_voted:
                error_msg = QGuiApplication.translate("VoterSearchController", "Voter has already voted")
                self._set_error_message(error_msg)
                self.operationFailed.emit(error_msg)
                return

            try:
                with get_session() as session:
                    # Mark voter as voted
                    updated_voter = mark_voted(UUID(voter_id), UUID(operator_id), session)
                    session.commit()

                    # Update DTO
                    updated_dto = self._convert_voter_to_dto(updated_voter, session)

                    # Update selected voter if it's the same
                    if self._selected_voter and self._selected_voter.id == voter_id:
                        self._set_selected_voter(updated_dto)

                    # Update search results
                    updated_results = []
                    for voter in self._search_results:
                        if voter.id == voter_id:
                            updated_results.append(updated_dto)
                        else:
                            updated_results.append(voter)
                    self._set_search_results(updated_results)

                    # Record performance metrics
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    self._record_mark_performance(elapsed_ms)

                    logger.info(f"Voter {updated_voter.voter_number} marked as voted")
                    logger.debug(f"Vote marking executed in {elapsed_ms:.1f} ms")
                    self.voterMarkedSuccessfully.emit(updated_voter.full_name)

            except ConnectionError as e:
                error_msg = QGuiApplication.translate("VoterSearchController", "Database connection failed")
                logger.error(f"Database connection error in markVoterAsVoted: {e}")
                self._set_error_message(error_msg)
                self.operationFailed.emit(error_msg)
            except ValueError as e:
                # Vote marking conflict (already voted, etc.)
                if "already voted" in str(e).lower():
                    error_msg = QGuiApplication.translate("VoterSearchController", "Voter has already voted")
                else:
                    error_msg = QGuiApplication.translate("VoterSearchController", "Invalid voting data")
                logger.warning(f"Voter marking validation error: {e}")
                self._set_error_message(error_msg)
                self.operationFailed.emit(error_msg)
            except Exception as e:
                error_msg = QGuiApplication.translate("VoterSearchController", "Failed to record vote")
                logger.error(f"Failed to mark voter {voter_id} as voted: {e}")
                self._set_error_message(error_msg)
                self.operationFailed.emit(error_msg)

        except Exception as e:
            error_msg = QGuiApplication.translate("VoterSearchController", "Unexpected error occurred")
            logger.error(f"Unexpected error in markVoterAsVoted: {e}")
            self._set_error_message(error_msg)
            self.operationFailed.emit(error_msg)
        finally:
            self._set_is_loading(False)

    @Slot()
    def clearSelection(self) -> None:
        """Clear selected voter and any errors."""
        self._set_selected_voter(None)
        self._set_error_message("")  # Clear errors when clearing selection
        logger.debug("Cleared voter selection")

    @Slot()
    def refreshSearch(self) -> None:
        """Re-execute current search with error handling."""
        if self._search_query:
            self._set_error_message("")  # Clear previous errors
            self._perform_search()
        else:
            error_msg = QGuiApplication.translate("VoterSearchController", "Enter a search term")
            self._set_error_message(error_msg)
            self.operationFailed.emit(error_msg)
            self.focusSearchBar()

    @Slot()
    def focusSearchBar(self) -> None:
        """Request focus on search bar (useful after errors)."""
        self.searchBarFocusRequested.emit()
        logger.debug("Requested focus on search bar")

    def _perform_search(self) -> None:
        """Execute search query with performance monitoring and error handling."""
        if not self._search_query:
            self._set_search_results([])
            return

        try:
            self._set_is_loading(True)
            self._set_error_message("")  # Clear previous errors
            start_time = time.perf_counter()

            try:
                with get_session() as session:
                    # Build search query
                    query = self._build_search_query(self._search_query)
                    db_voters: list[Voter] = list(session.exec(query).all())

                    # Convert to DTOs
                    voter_dtos = [
                        self._convert_voter_to_dto(voter, session) for voter in db_voters
                    ]

                    elapsed_ms = (time.perf_counter() - start_time) * 1000

                    # Record performance metrics
                    self._record_search_performance(elapsed_ms)

                    # Check for search timeout
                    if elapsed_ms > self._search_timeout_threshold_ms:
                        error_msg = QGuiApplication.translate("VoterSearchController", "Search took too long, please refine your query")
                        logger.warning(f"Search timeout: {elapsed_ms:.1f}ms > {self._search_timeout_threshold_ms}ms")
                        self._set_error_message(error_msg)
                        self.operationFailed.emit(error_msg)
                        # Still show results but warn user

                    # Create search result DTO
                    search_result = SearchResultDTO(
                        voters=voter_dtos,
                        total_count=len(voter_dtos),
                        search_query=self._search_query,
                        execution_time_ms=int(elapsed_ms),
                    )

                    self._set_search_results(search_result.voters)

                    logger.debug(
                        f"Search for '{self._search_query}' returned {len(voter_dtos)} results in {elapsed_ms:.1f}ms"
                    )

            except ConnectionError as e:
                error_msg = QGuiApplication.translate("VoterSearchController", "Database connection failed")
                logger.error(f"Database connection error in search: {e}")
                self._set_error_message(error_msg)
                self.operationFailed.emit(error_msg)
            except Exception as e:
                error_msg = QGuiApplication.translate("VoterSearchController", "Search failed")
                logger.error(f"Search failed for query '{self._search_query}': {e}")
                self._set_error_message(error_msg)
                self.operationFailed.emit(error_msg)

        except Exception as e:
            error_msg = QGuiApplication.translate("VoterSearchController", "Unexpected error occurred")
            logger.error(f"Unexpected error in _perform_search: {e}")
            self._set_error_message(error_msg)
            self.operationFailed.emit(error_msg)
        finally:
            self._set_is_loading(False)

    def _build_search_query(self, query: str) -> Any:
        """Build optimized SQLModel Select for voter search excluding soft-deleted records."""
        # Normalize Arabic text (e.g. remove diacritics, unify alef variants)
        normalized = self._normalize_arabic_text(query)

        # Build SQLAlchemy/SQLModel query:
        #  - exact number match
        #  - starts-with number match
        #  - contains full_name, father_name
        # Use case() to rank exact=1, partial=2, name=3, else=4
        exact_number = col(Voter.voter_number) == query
        partial_number = col(Voter.voter_number).startswith(query)
        name_match = col(Voter.full_name).contains(normalized)
        father_match = col(Voter.father_name).contains(normalized)

        return (
            select(Voter)
            .where(
                # Exclude soft-deleted records
                Voter.deleted_at.is_(None),  # type: ignore[union-attr]
                or_(
                    exact_number,
                    partial_number,
                    name_match,
                    father_match,
                )
            )
            .order_by(
                case(
                    (exact_number, 1),
                    (partial_number, 2),
                    (name_match, 3),
                    else_=4,
                )
            )
            .limit(100)
        )

    def _normalize_arabic_text(self, text: str) -> str:
        """Normalize Arabic text for search.

        Strips diacritics (tashkīl), normalizes alef/hamza forms, removes tatweel.
        Returns lowercased string.
        """
        if not text:
            return ""

        # Remove tatweel (elongation character)
        text = text.replace("ـ", "")

        # Normalize alef and hamza variants to standard alef
        alef_variants = {
            "أ": "ا",  # alef with hamza above
            "إ": "ا",  # alef with hamza below
            "آ": "ا",  # alef with madda above
            "ٱ": "ا",  # alef wasla
        }
        for variant, standard in alef_variants.items():
            text = text.replace(variant, standard)

        # Replace teh marbuta with heh
        text = text.replace("ة", "ه")

        # Remove all Arabic diacritics (tashkīl)
        arabic_diacritics = {
            "َ",  # fatha
            "ُ",  # damma
            "ِ",  # kasra
            "ً",  # fathatan
            "ٌ",  # dammatan
            "ٍ",  # kasratan
            "ْ",  # sukun
            "ّ",  # shadda
            "ٰ",  # alef khanjariyya
            "ۗ",  # small high seen
            "ۘ",  # small high rounded zero
            "ۙ",  # small high upright rectangular zero
            "ۚ",  # small high dotless head of khah
            "ۛ",  # small high meem isolated form
            "ۜ",  # small high lam alef
            "۟",  # small high jeem
            "۠",  # small high rounded zero with two dots below
        }

        for diacritic in arabic_diacritics:
            text = text.replace(diacritic, "")

        # Convert to lowercase and strip whitespace
        return text.lower().strip()

    def _convert_voter_to_dto(self, voter: Voter, session: Session) -> VoterDTO:
        """Convert database Voter to VoterDTO."""
        # Get pen label
        pen_label = ""
        if voter.pen:
            pen_label = voter.pen.label

        # Get operator name if voted
        voted_by_operator = None
        if voter.voted_by_operator_id:
            operator = session.get(User, voter.voted_by_operator_id)
            if operator:
                voted_by_operator = operator.full_name

        return VoterDTO(
            id=str(voter.id),
            voter_number=voter.voter_number,
            full_name=voter.full_name,
            father_name=voter.father_name,
            mother_name=voter.mother_name,
            pen_label=pen_label,
            has_voted=voter.has_voted,
            voted_at=voter.voted_at,
            voted_by_operator=voted_by_operator,
        )

    def _record_search_performance(self, elapsed_ms: float) -> None:
        """Record search performance metrics."""
        self._set_last_search_time_ms(elapsed_ms)
        self._total_searches += 1

        # Update rolling average
        if self._total_searches == 1:
            self._avg_search_time_ms = elapsed_ms
        else:
            # Simple moving average
            self._avg_search_time_ms = (
                (self._avg_search_time_ms * (self._total_searches - 1) + elapsed_ms)
                / self._total_searches
            )

        logger.debug(f"Search performance: {elapsed_ms:.1f}ms (avg: {self._avg_search_time_ms:.1f}ms, total: {self._total_searches})")

    def _record_mark_performance(self, elapsed_ms: float) -> None:
        """Record vote marking performance metrics."""
        self._set_last_mark_time_ms(elapsed_ms)
        self._total_marks += 1

        # Update rolling average
        if self._total_marks == 1:
            self._avg_mark_time_ms = elapsed_ms
        else:
            # Simple moving average
            self._avg_mark_time_ms = (
                (self._avg_mark_time_ms * (self._total_marks - 1) + elapsed_ms)
                / self._total_marks
            )

        logger.debug(f"Mark performance: {elapsed_ms:.1f}ms (avg: {self._avg_mark_time_ms:.1f}ms, total: {self._total_marks})")

    @Slot()
    def resetPerformanceMetrics(self) -> None:
        """Reset all performance metrics."""
        self._set_last_search_time_ms(0.0)
        self._set_last_mark_time_ms(0.0)
        self._total_searches = 0
        self._total_marks = 0
        self._avg_search_time_ms = 0.0
        self._avg_mark_time_ms = 0.0
        self.performanceMetricChanged.emit()
        logger.info("Performance metrics reset")

    @Slot(str, str)
    def softDeleteVoter(self, voter_id: str, operator_id: str) -> None:
        """Soft delete voter and queue for sync."""
        try:
            with get_session() as session:
                soft_delete_voter(UUID(voter_id), UUID(operator_id), session)
                self.voterDeletedSuccessfully.emit(voter_id)
                self.refreshSearch()
        except Exception as e:
            error_msg = f"Delete failed: {str(e)}"
            logger.error(f"Failed to soft delete voter {voter_id}: {e}")
            self.operationFailed.emit(error_msg)
