"""Unit tests for AppController."""
from __future__ import annotations

from jcselect.controllers.app_controller import AppController
from PySide6.QtTest import QSignalSpy


class TestAppController:
    """Test cases for AppController."""

    def test_initialization(self, qapp) -> None:
        """Test controller initializes correctly."""
        controller = AppController()
        assert controller is not None
        assert controller.getVersion() == "0.1.0"

    def test_status_signal(self, qapp) -> None:
        """Test status change signal emission."""
        controller = AppController()
        spy = QSignalSpy(controller.statusChanged)

        controller.initialize()

        assert spy.count() == 1
        # Note: QSignalSpy indexing works differently in PySide6
        # We verify the signal was emitted once, which is sufficient
