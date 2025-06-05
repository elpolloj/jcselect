"""Main application controller."""
from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot


class AppController(QObject):
    """Main application controller handling core app logic."""

    # Signals
    statusChanged = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the application controller."""
        super().__init__(parent)
        logger.info("AppController initialized")

    @Slot()
    def initialize(self) -> None:
        """Initialize application components."""
        logger.info("Initializing application components")
        self.statusChanged.emit("Application ready")

    @Slot(result=str)
    def getVersion(self) -> str:
        """Get application version."""
        return "0.1.0"
