"""Unit tests for TallyController validation logic."""
import pytest
from unittest.mock import Mock

from jcselect.controllers.tally_controller import TallyController
from jcselect.models import BallotType


class TestTallyControllerValidation:
    """Test validation logic in TallyController."""

    @pytest.fixture
    def tally_controller(self):
        """Create a TallyController instance for testing."""
        controller = TallyController()
        # Mock the session and other dependencies
        controller._current_session = Mock()
        controller._current_session.id = "test-session"
        controller._current_pen_id = "test-pen"
        controller._current_operator_id = "test-operator"
        return controller

    def test_no_validation_warnings_for_normal_ballot(self, tally_controller):
        """Test that normal ballot with proper selections has no warnings."""
        # Set up normal ballot with 2 candidates (within limit)
        tally_controller._selected_candidates = {
            "party1": "candidate1",
            "party2": "candidate2"
        }
        tally_controller._selected_ballot_type = BallotType.NORMAL
        
        warnings = tally_controller._validate_current_ballot()
        
        assert warnings == []
        assert not tally_controller.hasValidationWarnings

    def test_over_vote_warning(self, tally_controller):
        """Test over-vote warning when selecting more than 3 candidates."""
        # Set up over-vote scenario (4 candidates > 3 limit)
        tally_controller._selected_candidates = {
            "party1": "candidate1",
            "party2": "candidate2", 
            "party3": "candidate3",
            "party4": "candidate4"
        }
        tally_controller._selected_ballot_type = BallotType.NORMAL
        
        warnings = tally_controller._validate_current_ballot()
        
        assert len(warnings) == 1
        assert "تحذير: عدد الأصوات أكثر من المسموح" in warnings[0]
        assert tally_controller.hasValidationWarnings

    def test_under_vote_notification(self, tally_controller):
        """Test under-vote notification when no candidates selected on normal ballot."""
        # Set up under-vote scenario (no candidates selected)
        tally_controller._selected_candidates = {}
        tally_controller._selected_ballot_type = BallotType.NORMAL
        
        warnings = tally_controller._validate_current_ballot()
        
        assert len(warnings) == 1
        assert "ملاحظة: لم يتم اختيار أي مرشح" in warnings[0]
        assert tally_controller.hasValidationWarnings

    def test_mixed_ballot_warning_white(self, tally_controller):
        """Test mixed ballot warning when selecting candidates with white ballot."""
        # Set up mixed ballot scenario (candidates + white ballot type)
        tally_controller._selected_candidates = {
            "party1": "candidate1"
        }
        tally_controller._selected_ballot_type = BallotType.WHITE
        
        warnings = tally_controller._validate_current_ballot()
        
        assert len(warnings) == 1
        assert "تحذير: اختيار مرشحين مع نوع ورقة خاص" in warnings[0]
        assert tally_controller.hasValidationWarnings

    def test_mixed_ballot_warning_illegal(self, tally_controller):
        """Test mixed ballot warning when selecting candidates with illegal ballot."""
        # Set up mixed ballot scenario (candidates + illegal ballot type)
        tally_controller._selected_candidates = {
            "party1": "candidate1",
            "party2": "candidate2"
        }
        tally_controller._selected_ballot_type = BallotType.ILLEGAL
        
        warnings = tally_controller._validate_current_ballot()
        
        assert len(warnings) == 1
        assert "تحذير: اختيار مرشحين مع نوع ورقة خاص" in warnings[0]
        assert tally_controller.hasValidationWarnings

    def test_mixed_ballot_warning_cancel(self, tally_controller):
        """Test mixed ballot warning when selecting candidates with cancel ballot."""
        # Set up mixed ballot scenario (candidates + cancel ballot type)
        tally_controller._selected_candidates = {
            "party1": "candidate1"
        }
        tally_controller._selected_ballot_type = BallotType.CANCEL
        
        warnings = tally_controller._validate_current_ballot()
        
        assert len(warnings) == 1
        assert "تحذير: اختيار مرشحين مع نوع ورقة خاص" in warnings[0]
        assert tally_controller.hasValidationWarnings

    def test_mixed_ballot_warning_blank(self, tally_controller):
        """Test mixed ballot warning when selecting candidates with blank ballot."""
        # Set up mixed ballot scenario (candidates + blank ballot type)
        tally_controller._selected_candidates = {
            "party1": "candidate1"
        }
        tally_controller._selected_ballot_type = BallotType.BLANK
        
        warnings = tally_controller._validate_current_ballot()
        
        assert len(warnings) == 1
        assert "تحذير: اختيار مرشحين مع نوع ورقة خاص" in warnings[0]
        assert tally_controller.hasValidationWarnings

    def test_multiple_warnings(self, tally_controller):
        """Test multiple warnings can be generated simultaneously."""
        # Set up scenario with both over-vote and mixed ballot
        tally_controller._selected_candidates = {
            "party1": "candidate1",
            "party2": "candidate2",
            "party3": "candidate3",
            "party4": "candidate4"  # Over-vote
        }
        tally_controller._selected_ballot_type = BallotType.WHITE  # Mixed ballot
        
        warnings = tally_controller._validate_current_ballot()
        
        assert len(warnings) == 2
        assert any("عدد الأصوات أكثر من المسموح" in w for w in warnings)
        assert any("اختيار مرشحين مع نوع ورقة خاص" in w for w in warnings)
        assert tally_controller.hasValidationWarnings

    def test_special_ballot_types_no_warnings(self, tally_controller):
        """Test that special ballot types alone generate no warnings."""
        special_types = [BallotType.WHITE, BallotType.ILLEGAL, BallotType.CANCEL, BallotType.BLANK]
        
        for ballot_type in special_types:
            tally_controller._selected_candidates = {}  # No candidates
            tally_controller._selected_ballot_type = ballot_type
            
            warnings = tally_controller._validate_current_ballot()
            
            assert warnings == []
            assert not tally_controller.hasValidationWarnings

    def test_validation_changed_signal_emission(self, tally_controller):
        """Test that validationChanged signal is emitted when validation results change."""
        # Mock the signal
        signal_mock = Mock()
        tally_controller.validationChanged.connect(signal_mock)
        
        # First validation with warnings
        tally_controller._selected_candidates = {
            "party1": "candidate1",
            "party2": "candidate2",
            "party3": "candidate3",
            "party4": "candidate4"  # Over-vote
        }
        tally_controller._selected_ballot_type = BallotType.NORMAL
        
        tally_controller._validate_current_ballot()
        
        # Verify signal was emitted
        signal_mock.assert_called()
        assert tally_controller.hasValidationWarnings
        
        # Clear the mock and change to valid state
        signal_mock.reset_mock()
        tally_controller._selected_candidates = {
            "party1": "candidate1",
            "party2": "candidate2"  # Valid selection
        }
        
        tally_controller._validate_current_ballot()
        
        # Verify signal was emitted again
        signal_mock.assert_called()
        assert not tally_controller.hasValidationWarnings

    def test_validation_messages_property_updates(self, tally_controller):
        """Test that validationMessages property is updated correctly."""
        # Test with no warnings
        tally_controller._selected_candidates = {"party1": "candidate1"}
        tally_controller._selected_ballot_type = BallotType.NORMAL
        
        tally_controller._validate_current_ballot()
        
        assert tally_controller.validationMessages == []
        
        # Test with warnings
        tally_controller._selected_candidates = {
            "party1": "candidate1",
            "party2": "candidate2",
            "party3": "candidate3",
            "party4": "candidate4"  # Over-vote
        }
        
        tally_controller._validate_current_ballot()
        
        messages = tally_controller.validationMessages
        assert len(messages) == 1
        assert "تحذير: عدد الأصوات أكثر من المسموح" in messages[0]

    def test_lebanese_election_rules_limit(self, tally_controller):
        """Test that the validation follows Lebanese election rules (max 3 candidates)."""
        # Test exactly at the limit (3 candidates) - should be valid
        tally_controller._selected_candidates = {
            "party1": "candidate1",
            "party2": "candidate2",
            "party3": "candidate3"
        }
        tally_controller._selected_ballot_type = BallotType.NORMAL
        
        warnings = tally_controller._validate_current_ballot()
        
        assert warnings == []
        assert not tally_controller.hasValidationWarnings
        
        # Test over the limit (4 candidates) - should warn
        tally_controller._selected_candidates["party4"] = "candidate4"
        
        warnings = tally_controller._validate_current_ballot()
        
        assert len(warnings) == 1
        assert "تحذير: عدد الأصوات أكثر من المسموح" in warnings[0]
        assert tally_controller.hasValidationWarnings 