"""Unit tests for PenPickerController."""
from __future__ import annotations

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from PySide6.QtCore import QCoreApplication

from jcselect.controllers.pen_picker_controller import PenPickerController
from jcselect.models.pen import Pen


@pytest.fixture
def app():
    """Create QCoreApplication for Qt tests."""
    # Check if an application already exists
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app


@pytest.fixture
def pen_picker_controller(app):
    """Create PenPickerController instance."""
    return PenPickerController()


@pytest.fixture
def mock_pens():
    """Create mock pen data."""
    return [
        Pen(
            id=uuid4(),
            label="Pen 101",
            town_name="Beirut Central"
        ),
        Pen(
            id=uuid4(),
            label="Pen 102", 
            town_name="Tripoli North"
        )
    ]


class TestPenPickerController:
    """Test cases for PenPickerController."""

    def test_loadAvailablePens_returns_list(self, pen_picker_controller, mock_pens):
        """Test that loadAvailablePens returns a list of pens."""
        # Track signal emissions
        pens_loaded_emitted = False
        error_occurred_emitted = False
        
        def on_pens_loaded():
            nonlocal pens_loaded_emitted
            pens_loaded_emitted = True
            
        def on_error_occurred(error):
            nonlocal error_occurred_emitted
            error_occurred_emitted = True
        
        pen_picker_controller.pensLoaded.connect(on_pens_loaded)
        pen_picker_controller.errorOccurred.connect(on_error_occurred)
        
        # Mock the database session and query
        with patch('jcselect.controllers.pen_picker_controller.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = mock_pens
            
            # Execute the method
            pen_picker_controller.loadAvailablePens()
            
            # Verify results
            assert pens_loaded_emitted, "pensLoaded signal should be emitted"
            assert not error_occurred_emitted, "errorOccurred signal should not be emitted"
            
            available_pens = pen_picker_controller.availablePens
            assert len(available_pens) == 2, "Should have 2 available pens"
            
            # Check first pen data
            pen1 = available_pens[0]
            assert pen1["id"] == str(mock_pens[0].id)
            assert pen1["label"] == "Pen 101"
            assert pen1["town_name"] == "Beirut Central"

    def test_selectPen_valid_id_emits_selectionCompleted(self, pen_picker_controller, mock_pens):
        """Test that selectPen emits selectionCompleted for valid pen ID."""
        # Track signal emissions
        selection_completed_emitted = False
        selected_pen_id = None
        error_occurred_emitted = False
        
        def on_selection_completed(pen_id):
            nonlocal selection_completed_emitted, selected_pen_id
            selection_completed_emitted = True
            selected_pen_id = pen_id
            
        def on_error_occurred(error):
            nonlocal error_occurred_emitted
            error_occurred_emitted = True
        
        pen_picker_controller.selectionCompleted.connect(on_selection_completed)
        pen_picker_controller.errorOccurred.connect(on_error_occurred)
        
        test_pen_id = str(mock_pens[0].id)
        
        # Mock the database session and query
        with patch('jcselect.controllers.pen_picker_controller.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_pens[0]
            
            # Execute the method
            pen_picker_controller.selectPen(test_pen_id)
            
            # Verify results
            assert selection_completed_emitted, "selectionCompleted signal should be emitted"
            assert not error_occurred_emitted, "errorOccurred signal should not be emitted"
            assert selected_pen_id == test_pen_id, "Selected pen ID should match input"

    def test_selectPen_invalid_id_emits_errorOccurred(self, pen_picker_controller):
        """Test that selectPen emits errorOccurred for invalid pen ID."""
        # Track signal emissions
        selection_completed_emitted = False
        error_occurred_emitted = False
        error_message = None
        
        def on_selection_completed(pen_id):
            nonlocal selection_completed_emitted
            selection_completed_emitted = True
            
        def on_error_occurred(error):
            nonlocal error_occurred_emitted, error_message
            error_occurred_emitted = True
            error_message = error
        
        pen_picker_controller.selectionCompleted.connect(on_selection_completed)
        pen_picker_controller.errorOccurred.connect(on_error_occurred)
        
        invalid_pen_id = str(uuid4())
        
        # Mock the database session to return None (pen not found)
        with patch('jcselect.controllers.pen_picker_controller.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = None
            
            # Execute the method
            pen_picker_controller.selectPen(invalid_pen_id)
            
            # Verify results
            assert not selection_completed_emitted, "selectionCompleted signal should not be emitted"
            assert error_occurred_emitted, "errorOccurred signal should be emitted"
            assert "not valid" in error_message.lower(), "Error message should indicate invalid pen"

    def test_loadAvailablePens_database_error_emits_errorOccurred(self, pen_picker_controller):
        """Test that loadAvailablePens emits errorOccurred when database fails."""
        # Track signal emissions
        pens_loaded_emitted = False
        error_occurred_emitted = False
        error_message = None
        
        def on_pens_loaded():
            nonlocal pens_loaded_emitted
            pens_loaded_emitted = True
            
        def on_error_occurred(error):
            nonlocal error_occurred_emitted, error_message
            error_occurred_emitted = True
            error_message = error
        
        pen_picker_controller.pensLoaded.connect(on_pens_loaded)
        pen_picker_controller.errorOccurred.connect(on_error_occurred)
        
        # Mock the database session to raise an exception
        with patch('jcselect.controllers.pen_picker_controller.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")
            
            # Execute the method
            pen_picker_controller.loadAvailablePens()
            
            # Verify results
            assert not pens_loaded_emitted, "pensLoaded signal should not be emitted"
            assert error_occurred_emitted, "errorOccurred signal should be emitted"
            assert "failed to load" in error_message.lower(), "Error message should indicate load failure" 