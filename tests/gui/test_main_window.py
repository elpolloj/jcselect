"""GUI tests for main application window."""
from __future__ import annotations

import pytest


class TestMainWindow:
    """Test cases for main application window."""

    @pytest.mark.skip(reason="GUI test - enable when needed")
    def test_window_opens(self, qapp, qtbot) -> None:
        """Test that main window opens successfully."""
        # This would require more sophisticated QML testing setup
        # For now, we'll rely on manual testing
        pass
