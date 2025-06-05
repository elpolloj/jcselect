"""Pytest configuration and fixtures."""
from __future__ import annotations

from collections.abc import Generator

import pytest
from jcselect.models import *  # Import all models to register them
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture(scope="function")
def qml_engine():
    """Create QML engine for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    engine = QQmlApplicationEngine()
    
    # Add import paths
    engine.addImportPath("src/jcselect/ui")
    
    yield engine
    
    # Cleanup
    engine.clearComponentCache()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database session for testing."""
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Create session
    session = Session(engine)

    try:
        yield session
    finally:
        session.close()
