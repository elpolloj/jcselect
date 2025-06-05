# jcselect Project Bootstrap - Technical Specification

## 1. Project Overview

**jcselect** is an offline-first desktop voter tracking application built with Python 3.11, PySide 6/QML, SQLModel, and FastAPI. This bootstrap phase establishes the foundational project structure, development tooling, and CI/CD pipeline.

### 1.1 Architecture Overview
jcselect/
├── src/jcselect/           # Main application package
│   ├── ui/                 # QML UI components
│   ├── controllers/        # Python QObject controllers
│   ├── models/             # SQLModel data models
│   ├── dao.py             # Data Access Objects
│   ├── sync/              # Sync engine
│   ├── api/               # FastAPI backend
│   └── utils/             # Utilities and helpers
├── tests/                 # Test suite
├── scripts/               # Build and utility scripts
├── i18n/                  # Internationalization files
├── cursor-docs/           # Project documentation
└── resources/             # Static assets


## 2. Technical Requirements

### 2.1 Core Dependencies
- **Python**: 3.11+ (strict requirement)
- **UI Framework**: PySide 6 (Qt 6.x)
- **ORM**: SQLModel with SQLite (local) / PostgreSQL (cloud)
- **API**: FastAPI with pydantic v2
- **Build Tool**: Poetry for dependency management
- **Code Quality**: ruff, black, mypy with strict mode

### 2.2 Development Tools
- **Pre-commit**: Automated code quality checks
- **Testing**: pytest with pytest-qt for GUI testing
- **CI/CD**: GitHub Actions for Windows builds only
- **Type Checking**: mypy with --strict mode
- **Logging**: loguru for structured logging

### 2.3 Target Platforms
- **Primary**: Windows 10/11 (x64) only
- **Package Format**: Single-file executable via PyInstaller
- **Distribution**: PyUpdater for automatic updates

## 3. Detailed Implementation Plan

### Step 1: Initialize Poetry Project

bash
# Create new Poetry project with src layout
poetry new --src jcselect
cd jcselect

# Configure pyproject.toml


**pyproject.toml Configuration:**
toml
[tool.poetry]
name = "jcselect"
version = "0.1.0"
description = "Offline-first voter tracking system for Lebanon"
authors = ["Your Name <email@example.com>"]
readme = "README.md"
packages = [{include = "jcselect", from = "src"}]

[tool.poetry.dependencies]
python = "^3.11"
pyside6 = "^6.6.0"
sqlmodel = "^0.0.14"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
alembic = "^1.12.0"
loguru = "^0.7.2"
tenacity = "^8.2.3"
pydantic = "^2.5.0"
httpx = "^0.25.0"
cryptography = "^41.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-qt = "^4.2.0"
pytest-cov = "^4.1.0"
mypy = "^1.7.0"
ruff = "^0.1.6"
black = "^23.11.0"
pre-commit = "^3.5.0"
pyinstaller = "^6.2.0"

[tool.poetry.scripts]
jcselect = "jcselect.main:main"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"


### Step 2: Configure Code Quality Tools

**ruff.toml:**
toml
target-version = "py311"
line-length = 88
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long, handled by black
]

[per-file-ignores]
"__init__.py" = ["F401"]
"tests/*" = ["S101"]  # allow assert in tests


**mypy.ini:**
ini
[mypy]
python_version = 3.11
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[mypy-PySide6.*]
ignore_missing_imports = true

[mypy-sqlmodel.*]
ignore_missing_imports = true


**.pre-commit-config.yaml:**
yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--strict]


### Step 3: Create Project Structure

bash
# Create directory structure
mkdir -p src/jcselect/{ui,controllers,models,sync,api,utils}
mkdir -p tests/{unit,integration,gui}
mkdir -p scripts
mkdir -p i18n
mkdir -p resources/{icons,qml,themes}


**Directory Structure with __init__.py files:**
src/jcselect/
├── __init__.py
├── main.py                 # Application entry point
├── dao.py                 # Data Access Objects
├── ui/
│   ├── __init__.py
│   ├── App.qml            # Root QML component
│   └── Theme.qml          # Material 3 theme definitions
├── controllers/
│   ├── __init__.py
│   └── app_controller.py  # Main application controller
├── models/
│   ├── __init__.py
│   └── base.py           # Base SQLModel classes
├── sync/
│   ├── __init__.py
│   └── engine.py         # Sync engine
├── api/
│   ├── __init__.py
│   └── main.py           # FastAPI app
└── utils/
    ├── __init__.py
    ├── logging.py        # Loguru configuration
    └── constants.py      # Application constants


### Step 4: Implement Bootstrap Code

**src/jcselect/main.py:**
python
"""jcselect application entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, qmlRegisterType
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from jcselect.controllers.app_controller import AppController
from jcselect.utils.logging import setup_logging


def main() -> int:
    """Initialize and run the jcselect application."""
    setup_logging()
    
    # Set application properties
    QCoreApplication.setApplicationName("jcselect")
    QCoreApplication.setApplicationVersion("0.1.0")
    QCoreApplication.setOrganizationName("Lebanon Elections")
    
    app = QGuiApplication(sys.argv)
    
    # Enable RTL layout for Arabic
    app.setLayoutDirection(Qt.RightToLeft)
    
    # Register QML types
    qmlRegisterType(AppController, "jcselect", 1, 0, "AppController")
    
    # Create QML engine
    engine = QQmlApplicationEngine()
    
    # Set QML import paths - this enables Theme.qml singleton import
    ui_path = Path(__file__).parent / "ui"
    engine.addImportPath(str(ui_path))
    
    # Load main QML file
    qml_file = ui_path / "App.qml"
    engine.load(qml_file)
    
    if not engine.rootObjects():
        return 1
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())


**src/jcselect/ui/App.qml:**
qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect 1.0

ApplicationWindow {
    id: root
    
    width: 1200
    height: 800
    visible: true
    title: qsTr("jcselect - Voter Tracking System")
    
    // Enable RTL mirroring for Arabic
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true
    
    // Application controller
    AppController {
        id: appController
    }
    
    // Main content area
    Rectangle {
        anchors.fill: parent
        color: Theme.backgroundColor
        
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 20
            
            Text {
                text: qsTr("jcselect")
                font.pixelSize: 32
                font.weight: Font.Bold
                color: Theme.primaryColor
                Layout.alignment: Qt.AlignHCenter
            }
            
            Text {
                text: qsTr("Voter Tracking System")
                font.pixelSize: 16
                color: Theme.textColor
                Layout.alignment: Qt.AlignHCenter
            }
            
            Text {
                text: qsTr("Bootstrap Complete ✓")
                font.pixelSize: 14
                color: Theme.successColor
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}


**src/jcselect/ui/Theme.qml:**
qml
pragma Singleton
import QtQuick 2.15

QtObject {
    // Material 3 color tokens
    readonly property color primaryColor: "#1976D2"
    readonly property color backgroundColor: "#FFFFFF"
    readonly property color surfaceColor: "#F5F5F5"
    readonly property color textColor: "#212121"
    readonly property color successColor: "#4CAF50"
    readonly property color errorColor: "#F44336"
    readonly property color warningColor: "#FF9800"
    
    // Typography
    readonly property int headlineSize: 32
    readonly property int titleSize: 20
    readonly property int bodySize: 14
    readonly property int captionSize: 12
    
    // Spacing
    readonly property int spacing: 16
    readonly property int margin: 24
    readonly property int radius: 8
}


**src/jcselect/controllers/app_controller.py:**
python
"""Main application controller."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot
from loguru import logger


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


**src/jcselect/utils/logging.py:**
python
"""Logging configuration using loguru."""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging() -> None:
    """Configure loguru logging for the application."""
    # Remove default handler
    logger.remove()
    
    # Add console handler with formatting
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level="INFO",
    )
    
    # Add file handler for persistent logging
    log_dir = Path.home() / ".jcselect" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_dir / "jcselect.log",
        rotation="10 MB",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    logger.info("Logging configured")


**src/jcselect/dao.py:**
python
"""Data Access Objects for jcselect."""
from __future__ import annotations

from loguru import logger


class BaseDAO:
    """Base Data Access Object with common functionality."""
    
    def __init__(self) -> None:
        """Initialize the DAO."""
        logger.info("BaseDAO initialized")


### Step 5: Create qmldir for Theme

**src/jcselect/ui/qmldir:**
module jcselect.ui
singleton Theme 1.0 Theme.qml


### Step 6: Add Test Infrastructure

**tests/conftest.py:**
python
"""Pytest configuration and fixtures."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


**tests/unit/test_app_controller.py:**
python
"""Unit tests for AppController."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QSignalSpy

from jcselect.controllers.app_controller import AppController


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
        
        assert len(spy) == 1
        assert spy[0][0] == "Application ready"


**tests/gui/test_main_window.py:**
python
"""GUI tests for main application window."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from jcselect.main import main


class TestMainWindow:
    """Test cases for main application window."""
    
    @pytest.mark.skip(reason="GUI test - enable when needed")
    def test_window_opens(self, qapp, qtbot) -> None:
        """Test that main window opens successfully."""
        # This would require more sophisticated QML testing setup
        # For now, we'll rely on manual testing
        pass


## 4. Execution Steps

Execute these commands in order:

bash
# 1. Initialize Poetry project
poetry new --src jcselect
cd jcselect

# 2. Configure pyproject.toml (copy content above)

# 3. Install dependencies
poetry install

# 4. Create directory structure
mkdir -p src/jcselect/{ui,controllers,models,sync,api,utils}
mkdir -p tests/{unit,integration,gui}
mkdir -p scripts i18n resources/{icons,qml,themes}
mkdir -p .github/workflows

# 5. Create all __init__.py files
touch src/jcselect/__init__.py
touch src/jcselect/{ui,controllers,models,sync,api,utils}/__init__.py
touch tests/__init__.py

# 6. Create all source files (copy content from above)
# - src/jcselect/main.py
# - src/jcselect/dao.py
# - src/jcselect/ui/App.qml
# - src/jcselect/ui/Theme.qml
# - src/jcselect/ui/qmldir
# - src/jcselect/controllers/app_controller.py
# - src/jcselect/utils/logging.py
# - tests/conftest.py
# - tests/unit/test_app_controller.py
# - tests/gui/test_main_window.py

# 7. Create configuration files
# - ruff.toml
# - mypy.ini
# - .pre-commit-config.yaml
# - README.md

# 8. Install pre-commit hooks
poetry run pre-commit install

# 9. Run initial checks
poetry run pre-commit run --all-files

# 10. Run tests
poetry run pytest

# 11. Test application
poetry run python -m jcselect

## 5. Acceptance Criteria Verification

After completing all steps, verify:

- ✅ poetry install completes with no conflicts
- ✅ pre-commit run --all-files passes locally  
- ✅ pytest exits 0 with ≥ 1 test collected
- ✅ Running python -m jcselect opens a blank window with "Bootstrap Complete ✓"