"""Pen picker controller for pen selection dialog."""
from __future__ import annotations

from loguru import logger
from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlmodel import select

from jcselect.models.pen import Pen
from jcselect.utils.db import get_session


class PenPickerController(QObject):
    """Controller for pen selection dialog."""

    # Signals
    pensLoaded = Signal()
    selectionCompleted = Signal(str)  # pen_id
    errorOccurred = Signal(str)  # error_message

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize pen picker controller."""
        super().__init__(parent)
        self._available_pens: list[dict[str, str]] = []

    # Properties
    def _get_available_pens(self) -> list[dict[str, str]]:
        """Get available pens list."""
        return self._available_pens

    def _set_available_pens(self, value: list[dict[str, str]]) -> None:
        """Set available pens list."""
        self._available_pens = value

    availablePens = Property("QVariantList", _get_available_pens, _set_available_pens, notify=pensLoaded)  # type: ignore[call-arg,arg-type]

    @Slot()
    def loadAvailablePens(self) -> None:
        """Load available pens from database."""
        try:
            with get_session() as session:
                # Build query to get all active (non-deleted) pens
                query = select(Pen)

                # Check if Pen model has soft delete fields (deleted_at)
                if hasattr(Pen, 'deleted_at'):
                    query = query.where(Pen.deleted_at.is_(None))

                pens = session.exec(query).all()

                pen_list = []
                for pen in pens:
                    pen_dict = {
                        "id": str(pen.id),
                        "label": pen.label,
                        "town_name": pen.town_name
                    }
                    pen_list.append(pen_dict)

                self._available_pens = pen_list
                self.pensLoaded.emit()
                logger.info(f"Loaded {len(pen_list)} available pens")

        except Exception as e:
            logger.error(f"Failed to load pens: {e}")
            self.errorOccurred.emit(f"Failed to load polling stations: {str(e)}")

    @Slot(str)
    def selectPen(self, pen_id: str) -> None:
        """Select a pen and emit completion signal."""
        try:
            # Validate pen exists and is not deleted
            with get_session() as session:
                query = select(Pen).where(Pen.id == pen_id)

                # Check if Pen model has soft delete fields
                if hasattr(Pen, 'deleted_at'):
                    query = query.where(Pen.deleted_at.is_(None))

                pen = session.exec(query).first()

                if not pen:
                    self.errorOccurred.emit("Selected polling station is not valid or has been deleted")
                    return

            self.selectionCompleted.emit(pen_id)
            logger.info(f"Pen selected: {pen_id} ({pen.label})")

        except Exception as e:
            logger.error(f"Pen selection failed: {e}")
            self.errorOccurred.emit(f"Selection failed: {str(e)}")
