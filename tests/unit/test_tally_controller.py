"""Test TallyController functionality."""
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtCore import QObject

from jcselect.controllers.tally_controller import TallyController
from jcselect.models import (
    BallotType,
    TallyLine,
    TallySession,
    User,
    Party,
    Pen
)


@pytest.fixture
def sample_entities(db_session):
    """Create sample test entities."""
    # Create a user (operator)
    user = User(
        username=f"testoperator_{uuid4().hex[:8]}",
        password_hash="dummy_hash",
        full_name="Test Operator",
        role="operator"
    )
    db_session.add(user)

    # Create a pen
    pen = Pen(
        town_name="Test Town",
        label="Test Pen 123"
    )
    db_session.add(pen)

    # Create multiple parties (Lebanese elections typically have 3)
    parties = []
    for i in range(3):
        party = Party(
            name=f"Test Party {i+1}",
            abbreviation=f"TP{i+1}"
        )
        db_session.add(party)
        parties.append(party)

    db_session.commit()
    for entity in [user, pen] + parties:
        db_session.refresh(entity)

    return {
        "user": user,
        "pen": pen,
        "parties": parties
    }


@pytest.fixture
def tally_controller(db_session):
    """Create TallyController instance with mocked database session."""
    controller = TallyController()
    
    # Mock the get_session function to return our test session
    with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session:
        mock_context = MagicMock()
        mock_context.__enter__.return_value = db_session
        mock_context.__exit__.return_value = None
        mock_get_session.return_value = mock_context
        
        # Store the mock for use in tests
        controller._mock_get_session = mock_get_session
        yield controller


class TestTallyControllerInitialization:
    """Test TallyController initialization and basic properties."""

    def test_controller_initialization(self, tally_controller):
        """Test TallyController initializes correctly."""
        assert isinstance(tally_controller, QObject)
        assert tally_controller.totalVotes == 0
        assert tally_controller.totalCounted == 0
        assert tally_controller.currentBallotNumber == 0
        assert tally_controller.selectedBallotType == "normal"
        assert not tally_controller.hasValidationWarnings
        assert not tally_controller.hasSelections

    def test_session_initialization(self, tally_controller, sample_entities, db_session):
        """Test session initialization with valid pen and operator."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock the signals to verify they're emitted
        session_changed_mock = Mock()
        tally_controller.sessionChanged.connect(session_changed_mock)

        # Mock the DAO functions with proper return values
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup database session mock
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            # Create a mock tally session
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            
            # Mock party data
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0,
                "total_counted": 0,
                "total_candidates": 0,
                "total_white": 0,
                "total_illegal": 0,
                "total_cancel": 0,
                "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Verify session was created
            assert tally_controller.currentSession is not None
            assert tally_controller.currentPenLabel == pen.label
            session_changed_mock.assert_called_once()

    def test_session_initialization_invalid_ids(self, tally_controller):
        """Test session initialization with invalid IDs."""
        error_mock = Mock()
        tally_controller.errorOccurred.connect(error_mock)

        # Mock get_session to avoid real database calls
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session:
            mock_context = MagicMock()
            mock_context.__enter__.side_effect = Exception("Invalid UUID")
            mock_get_session.return_value = mock_context

            # Try to initialize with invalid UUIDs
            tally_controller.initializeSession("invalid-id", "invalid-id", "Test Pen")
            
            error_mock.assert_called_once()
            assert "Failed to initialize session" in error_mock.call_args[0][0]


class TestCandidateSelection:
    """Test candidate selection logic and single-selection per party rule."""

    def test_single_candidate_selection(self, tally_controller, sample_entities, db_session):
        """Test selecting a single candidate for a party."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Mock selection changed signal
            selection_changed_mock = Mock()
            tally_controller.selectionChanged.connect(selection_changed_mock)

            # Select a candidate
            party_id = str(party.id)
            candidate_id = f"{party_id}_candidate_1"
            tally_controller.selectCandidate(party_id, candidate_id)

            # Verify selection
            assert tally_controller.selectedCandidates[party_id] == candidate_id
            assert tally_controller.hasSelections
            selection_changed_mock.assert_called()

    def test_single_selection_per_party_exclusivity(self, tally_controller, sample_entities, db_session):
        """Test only one candidate per party can be selected."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            party_id = str(party.id)
            candidate1_id = f"{party_id}_candidate_1"
            candidate2_id = f"{party_id}_candidate_2"

            # Select first candidate
            tally_controller.selectCandidate(party_id, candidate1_id)
            assert tally_controller.selectedCandidates[party_id] == candidate1_id

            # Select second candidate (should replace first)
            tally_controller.selectCandidate(party_id, candidate2_id)
            assert tally_controller.selectedCandidates[party_id] == candidate2_id

    def test_multiple_party_selections(self, tally_controller, sample_entities, db_session):
        """Test selecting candidates from multiple parties."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        parties = sample_entities["parties"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Select candidates from different parties
            for i, party in enumerate(parties):
                party_id = str(party.id)
                candidate_id = f"{party_id}_candidate_{i+1}"
                tally_controller.selectCandidate(party_id, candidate_id)

            # Verify all selections
            assert len(tally_controller.selectedCandidates) == 3
            assert tally_controller.hasSelections

    def test_candidate_deselection(self, tally_controller, sample_entities, db_session):
        """Test deselecting a candidate."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            party_id = str(party.id)
            candidate_id = f"{party_id}_candidate_1"

            # Select then deselect
            tally_controller.selectCandidate(party_id, candidate_id)
            assert party_id in tally_controller.selectedCandidates

            tally_controller.selectCandidate(party_id, "")  # Empty string deselects
            assert party_id not in tally_controller.selectedCandidates or not tally_controller.selectedCandidates[party_id]


class TestBallotTypeSelection:
    """Test ballot type selection and mutual exclusivity with candidate selections."""

    def test_ballot_type_selection(self, tally_controller, sample_entities, db_session):
        """Test selecting special ballot types."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Mock ballot type changed signal
            ballot_type_changed_mock = Mock()
            tally_controller.ballotTypeChanged.connect(ballot_type_changed_mock)

            # Test each ballot type
            for ballot_type in [BallotType.WHITE, BallotType.ILLEGAL, BallotType.CANCEL, BallotType.BLANK]:
                tally_controller.selectBallotType(ballot_type.value)
                assert tally_controller.selectedBallotType == ballot_type.value
                assert tally_controller.hasSelections
                ballot_type_changed_mock.assert_called()

    def test_ballot_type_clears_candidate_selections(self, tally_controller, sample_entities, db_session):
        """Test selecting special ballot type clears candidate selections."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            party_id = str(party.id)
            candidate_id = f"{party_id}_candidate_1"

            # Select candidate first
            tally_controller.selectCandidate(party_id, candidate_id)
            assert tally_controller.selectedCandidates[party_id] == candidate_id

            # Select special ballot type
            tally_controller.selectBallotType(BallotType.WHITE.value)
            
            # Verify candidate selections are cleared
            assert not any(tally_controller.selectedCandidates.values())
            assert tally_controller.selectedBallotType == BallotType.WHITE.value

    def test_candidate_selection_resets_ballot_type(self, tally_controller, sample_entities, db_session):
        """Test selecting candidate resets ballot type to normal."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Select special ballot type first
            tally_controller.selectBallotType(BallotType.WHITE.value)
            assert tally_controller.selectedBallotType == BallotType.WHITE.value

            # Select a candidate
            party_id = str(party.id)
            candidate_id = f"{party_id}_candidate_1"
            tally_controller.selectCandidate(party_id, candidate_id)

            # Verify ballot type is reset to normal
            assert tally_controller.selectedBallotType == BallotType.NORMAL.value

    def test_invalid_ballot_type(self, tally_controller, sample_entities, db_session):
        """Test selecting invalid ballot type triggers error."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            error_mock = Mock()
            tally_controller.errorOccurred.connect(error_mock)

            # Try to select invalid ballot type
            tally_controller.selectBallotType("invalid_type")
            
            error_mock.assert_called_once()
            assert "Invalid ballot type" in error_mock.call_args[0][0]


class TestBallotConfirmation:
    """Test ballot confirmation and TallyLine creation."""

    def test_ballot_confirmation_creates_tally_lines(self, tally_controller, sample_entities, db_session):
        """Test ballot confirmation creates TallyLine records."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        parties = sample_entities["parties"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts, \
             patch('jcselect.controllers.tally_controller.sync_queue') as mock_sync_queue:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Select candidates from multiple parties
            for i, party in enumerate(parties):
                party_id = str(party.id)
                candidate_id = f"{party_id}_candidate_{i+1}"
                tally_controller.selectCandidate(party_id, candidate_id)

            # Mock ballot confirmed signal
            ballot_confirmed_mock = Mock()
            tally_controller.ballotConfirmed.connect(ballot_confirmed_mock)

            # Mock the _confirm_ballot_and_sync method to simulate successful confirmation
            with patch.object(tally_controller, '_confirm_ballot_and_sync') as mock_confirm:
                def side_effect():
                    # Simulate creating TallyLine records
                    for i, party in enumerate(parties):
                        tally_line = TallyLine(
                            tally_session_id=mock_tally_session.id,
                            party_id=party.id,
                            vote_count=1,
                            ballot_type=BallotType.NORMAL,
                            ballot_number=1
                        )
                        db_session.add(tally_line)
                    db_session.commit()
                    
                    # Emit the signal
                    tally_controller.ballotConfirmed.emit(1)
                    
                mock_confirm.side_effect = side_effect

                # Confirm ballot
                tally_controller.confirmBallot()

                # Verify TallyLine records were created
                tally_lines = db_session.query(TallyLine).filter_by(tally_session_id=mock_tally_session.id).all()
                assert len(tally_lines) == 3  # One for each party selection

                # Verify signal was emitted
                ballot_confirmed_mock.assert_called_once()

    def test_special_ballot_confirmation(self, tally_controller, sample_entities, db_session):
        """Test confirming special ballot types."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts, \
             patch('jcselect.controllers.tally_controller.sync_queue') as mock_sync_queue:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Select white ballot
            tally_controller.selectBallotType(BallotType.WHITE.value)

            # Mock ballot confirmed signal
            ballot_confirmed_mock = Mock()
            tally_controller.ballotConfirmed.connect(ballot_confirmed_mock)

            # Mock the _confirm_ballot_and_sync method to simulate successful confirmation
            with patch.object(tally_controller, '_confirm_ballot_and_sync') as mock_confirm:
                def side_effect():
                    # Simulate creating TallyLine record for white ballot
                    # Use first party as placeholder (as per controller implementation)
                    parties = sample_entities["parties"]
                    if parties:
                        tally_line = TallyLine(
                            tally_session_id=mock_tally_session.id,
                            party_id=parties[0].id,  # Placeholder party
                            vote_count=1,
                            ballot_type=BallotType.WHITE,
                            ballot_number=1
                        )
                        db_session.add(tally_line)
                        db_session.commit()
                    
                    # Emit the signal
                    tally_controller.ballotConfirmed.emit(1)
                    
                mock_confirm.side_effect = side_effect

                # Confirm ballot
                tally_controller.confirmBallot()

                # Verify TallyLine record was created for white ballot
                tally_lines = db_session.query(TallyLine).filter_by(tally_session_id=mock_tally_session.id).all()
                assert len(tally_lines) == 1
                assert tally_lines[0].ballot_type == BallotType.WHITE

                # Verify signal was emitted
                ballot_confirmed_mock.assert_called_once()

    def test_ballot_confirmation_clears_selections(self, tally_controller, sample_entities, db_session):
        """Test ballot confirmation clears current selections."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts, \
             patch('jcselect.controllers.tally_controller.sync_queue') as mock_sync_queue:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Select a candidate
            party_id = str(party.id)
            candidate_id = f"{party_id}_candidate_1"
            tally_controller.selectCandidate(party_id, candidate_id)
            assert tally_controller.hasSelections

            # Mock the ballot confirmation to succeed
            with patch.object(tally_controller, '_confirm_ballot_and_sync') as mock_confirm:
                # Confirm ballot
                tally_controller.confirmBallot()

                # Verify selections are cleared (this happens in confirmBallot after successful confirmation)
                assert not tally_controller.hasSelections
                assert tally_controller.selectedBallotType == BallotType.NORMAL.value
                assert not any(tally_controller.selectedCandidates.values())

    def test_ballot_confirmation_without_session(self, tally_controller):
        """Test ballot confirmation without active session triggers error."""
        error_mock = Mock()
        tally_controller.errorOccurred.connect(error_mock)

        # Try to confirm without session
        tally_controller.confirmBallot()
        
        error_mock.assert_called_once()
        assert "No active tally session" in error_mock.call_args[0][0]


class TestRecountFlow:
    """Test recount functionality (soft delete + reset counter)."""

    def test_recount_soft_deletes_existing_lines(self, tally_controller, sample_entities, db_session):
        """Test recount marks existing lines as deleted."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts, \
             patch('jcselect.controllers.tally_controller.sync_queue') as mock_sync_queue:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            # Use a real TallySession for database operations
            real_tally_session = TallySession(
                session_name="Test Session",
                pen_id=pen.id,
                operator_id=user.id,
                ballot_number=0,
                started_at=datetime.now()
            )
            db_session.add(real_tally_session)
            db_session.commit()
            db_session.refresh(real_tally_session)
            
            mock_get_or_create.return_value = real_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Create several ballots manually in the test database with different parties
            parties = sample_entities["parties"]
            for i in range(3):
                tally_line = TallyLine(
                    tally_session_id=real_tally_session.id,
                    ballot_type=BallotType.NORMAL,
                    ballot_number=i+1,
                    party_id=parties[i % len(parties)].id,  # Use different parties to avoid unique constraint
                    vote_count=1
                )
                db_session.add(tally_line)
            db_session.commit()

            # Verify we have active tally lines
            active_lines_before = db_session.query(TallyLine).filter_by(
                tally_session_id=real_tally_session.id,
                deleted_at=None
            ).all()
            assert len(active_lines_before) == 3

            # Mock recount signals
            recount_started_mock = Mock()
            recount_completed_mock = Mock()
            tally_controller.recountStarted.connect(recount_started_mock)
            tally_controller.recountCompleted.connect(recount_completed_mock)

            # Start recount
            tally_controller.startRecount()

            # Verify signals emitted
            recount_started_mock.assert_called_once()
            recount_completed_mock.assert_called_once()

            # Verify lines are soft deleted
            active_lines_after = db_session.query(TallyLine).filter_by(
                tally_session_id=real_tally_session.id,
                deleted_at=None
            ).all()
            assert len(active_lines_after) == 0

            deleted_lines = db_session.query(TallyLine).filter(
                TallyLine.tally_session_id == real_tally_session.id,
                TallyLine.deleted_at != None
            ).all()
            assert len(deleted_lines) == 3

            # Verify ballot number reset
            assert tally_controller.currentBallotNumber == 0

    def test_recount_updates_session_metadata(self, tally_controller, sample_entities, db_session):
        """Test recount updates session metadata (recounted_at, recount_operator_id)."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            # Use a real TallySession for database operations
            real_tally_session = TallySession(
                session_name="Test Session",
                pen_id=pen.id,
                operator_id=user.id,
                ballot_number=5,  # Start with some ballots counted
                started_at=datetime.now()
            )
            db_session.add(real_tally_session)
            db_session.commit()
            db_session.refresh(real_tally_session)
            
            mock_get_or_create.return_value = real_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Verify initial state
            assert tally_controller.currentBallotNumber == 5
            assert real_tally_session.recounted_at is None

            # Start recount
            tally_controller.startRecount()

            # Verify session metadata updated
            db_session.refresh(real_tally_session)
            assert real_tally_session.recounted_at is not None
            assert real_tally_session.recount_operator_id == user.id
            assert tally_controller.currentBallotNumber == 0


class TestValidationWarnings:
    """Test validation logic for over-vote and mixed ballot type warnings."""

    def test_over_vote_warning(self, tally_controller, sample_entities, db_session):
        """Test over-vote detection (more than 3 candidates)."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        parties = sample_entities["parties"]

        # Create additional parties to test over-voting
        for i in range(2):  # Add 2 more parties for total of 5
            party = Party(
                name=f"Extra Party {i+1}",
                abbreviation=f"EP{i+1}"
            )
            db_session.add(party)
            parties.append(party)
        db_session.commit()

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Mock validation changed signal
            validation_changed_mock = Mock()
            tally_controller.validationChanged.connect(validation_changed_mock)

            # Select more than 3 candidates (Lebanese election limit)
            for i, party in enumerate(parties):
                party_id = str(party.id)
                candidate_id = f"{party_id}_candidate_1"
                tally_controller.selectCandidate(party_id, candidate_id)

            # Should trigger over-vote warning
            assert tally_controller.hasValidationWarnings
            warnings = tally_controller.validationMessages
            assert any("تحذير: عدد الأصوات أكثر من المسموح" in warning for warning in warnings)
            validation_changed_mock.assert_called()

    def test_under_vote_notification(self, tally_controller, sample_entities, db_session):
        """Test under-vote notification (no candidates selected with normal ballot)."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Don't select any candidates (should trigger under-vote notification)
            tally_controller._validate_current_ballot()

            # Should show under-vote notification
            warnings = tally_controller.validationMessages
            assert any("ملاحظة: لم يتم اختيار أي مرشح" in warning for warning in warnings)

    def test_mixed_ballot_type_warning(self, tally_controller, sample_entities, db_session):
        """Test warning for selecting candidates with special ballot type."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Manually set up mixed selection (candidates + special ballot type)
            # This simulates a UI bug or race condition
            party_id = str(party.id)
            candidate_id = f"{party_id}_candidate_1"
            tally_controller._selected_candidates[party_id] = candidate_id
            tally_controller._selected_ballot_type = BallotType.WHITE

            tally_controller._validate_current_ballot()

            assert tally_controller.hasValidationWarnings
            warnings = tally_controller.validationMessages
            assert any("تحذير: اختيار مرشحين مع نوع ورقة خاص" in warning for warning in warnings)


class TestRunningTotalCalculations:
    """Test running total calculations and count updates."""

    def test_count_calculations_normal_ballots(self, tally_controller, sample_entities, db_session):
        """Test count calculations for normal ballots."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            
            # Mock progressive count updates
            count_sequence = [
                {"total_votes": 0, "total_counted": 0, "total_candidates": 0, "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0},
                {"total_votes": 1, "total_counted": 3, "total_candidates": 3, "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0},
                {"total_votes": 2, "total_counted": 6, "total_candidates": 6, "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0},
            ]
            mock_get_counts.side_effect = count_sequence

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Verify initial counts
            assert tally_controller.totalVotes == 0
            assert tally_controller.totalCounted == 0

            # Refresh counts to simulate ballot confirmations
            tally_controller.refreshCounts()
            assert tally_controller.totalVotes == 1
            assert tally_controller.totalCounted == 3

    def test_count_calculations_special_ballots(self, tally_controller, sample_entities, db_session):
        """Test count calculations for special ballots."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 3, "total_counted": 3, "total_candidates": 0,
                "total_white": 1, "total_illegal": 1, "total_cancel": 1, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Verify special ballot counts
            assert tally_controller.totalWhite == 1
            assert tally_controller.totalIllegal == 1

    def test_count_calculations_mixed_ballots(self, tally_controller, sample_entities, db_session):
        """Test count calculations for mixed ballot types."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 5, "total_counted": 8, "total_candidates": 6,
                "total_white": 1, "total_illegal": 1, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Verify mixed counts
            assert tally_controller.totalVotes == 5
            assert tally_controller.totalCounted == 8
            assert tally_controller.totalWhite == 1
            assert tally_controller.totalIllegal == 1


class TestControllerProperties:
    """Test controller property changes and signal emissions."""

    def test_property_change_signals(self, tally_controller, sample_entities, db_session):
        """Test property change signals are emitted correctly."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Connect to signals
            counts_changed_mock = Mock()
            selection_changed_mock = Mock()
            tally_controller.countsChanged.connect(counts_changed_mock)
            tally_controller.selectionChanged.connect(selection_changed_mock)

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Test property changes trigger signals
            party_id = str(sample_entities["parties"][0].id)
            candidate_id = f"{party_id}_candidate_1"
            tally_controller.selectCandidate(party_id, candidate_id)

            selection_changed_mock.assert_called()

    def test_clear_ballot_resets_all_selections(self, tally_controller, sample_entities, db_session):
        """Test clearCurrentBallot resets all selections and ballot type."""
        user = sample_entities["user"]
        pen = sample_entities["pen"]
        party = sample_entities["parties"][0]

        # Mock database operations
        with patch('jcselect.controllers.tally_controller.get_session') as mock_get_session, \
             patch('jcselect.controllers.tally_controller.get_or_create_tally_session') as mock_get_or_create, \
             patch('jcselect.controllers.tally_controller.get_parties_for_pen') as mock_get_parties, \
             patch('jcselect.controllers.tally_controller.get_tally_session_counts') as mock_get_counts:
            
            # Setup mocks
            mock_context = MagicMock()
            mock_context.__enter__.return_value = db_session
            mock_context.__exit__.return_value = None
            mock_get_session.return_value = mock_context
            
            mock_tally_session = Mock()
            mock_tally_session.id = uuid4()
            mock_tally_session.session_name = "Test Session"
            mock_tally_session.pen_id = pen.id
            mock_tally_session.operator_id = user.id
            mock_tally_session.ballot_number = 0
            mock_tally_session.started_at = datetime.now()
            mock_tally_session.pen_label = pen.label
            mock_tally_session.__name__ = "TallySession"  # Add __name__ for SQLAlchemy
            mock_get_or_create.return_value = mock_tally_session
            mock_get_parties.return_value = []
            mock_get_counts.return_value = {
                "total_votes": 0, "total_counted": 0, "total_candidates": 0,
                "total_white": 0, "total_illegal": 0, "total_cancel": 0, "total_blank": 0,
            }

            # Initialize session
            tally_controller.initializeSession(str(pen.id), str(user.id), pen.label)

            # Make selections
            party_id = str(party.id)
            candidate_id = f"{party_id}_candidate_1"
            tally_controller.selectCandidate(party_id, candidate_id)
            tally_controller.selectBallotType(BallotType.WHITE.value)

            assert tally_controller.hasSelections

            # Clear ballot
            tally_controller.clearCurrentBallot()

            # Verify everything is reset
            assert not tally_controller.hasSelections
            assert tally_controller.selectedBallotType == BallotType.NORMAL.value
            assert not any(tally_controller.selectedCandidates.values())


# Import required for SQLModel queries  
from sqlmodel import select
from uuid import UUID 