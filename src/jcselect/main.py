"""jcselect application entry point."""
from __future__ import annotations

import asyncio
import os
import sys
import threading
from pathlib import Path

# Import logger for sync status
from loguru import logger
from PySide6.QtCore import QCoreApplication, QResource, Qt, QTranslator
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from jcselect.controllers.app_controller import AppController
from jcselect.controllers.results_controller import ResultsController
from jcselect.controllers.sync_status_controller import SyncStatusController
from jcselect.controllers.tally_controller import TallyController
from jcselect.controllers.voter_search_controller import VoterSearchController
from jcselect.utils.logging import configure_app_logging

# Import dashboard controllers
try:
    from jcselect.controllers.dashboard_controller import DashboardController
    from jcselect.controllers.login_controller import LoginController
    from jcselect.controllers.pen_picker_controller import PenPickerController
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    print("Warning: Dashboard controllers not available")


def register_resources() -> None:
    """Register Qt resources (QRC files)."""
    try:
        # For development, we'll use direct file paths to the resource directories
        # In production, QRC would be compiled to a Python resource module
        
        workspace_root = Path(__file__).parent.parent.parent  # Navigate to workspace root
        resources_path = workspace_root / "resources"
        icons_path = resources_path / "icons"
        
        # Check if resource directories exist
        if resources_path.exists() and icons_path.exists():
            print(f"✅ Icon resources found at {icons_path}")
            
            # Count available icons
            icon_count = len(list(icons_path.glob("*.svg")))
            print(f"✅ {icon_count} SVG icons available")
            
            # Test a few specific icons
            test_icons = ["voter-search.svg", "ballot-count.svg", "live-results.svg"]
            for icon in test_icons:
                icon_path = icons_path / icon
                if icon_path.exists():
                    print(f"  ✅ {icon} found")
                else:
                    print(f"  ⚠️  {icon} missing")
        else:
            print("⚠️  Resource directories not found, icons may not display")
            print(f"     Looked for: {resources_path}")
            
    except Exception as e:
        print(f"⚠️  Failed to register resources: {e}")


def run_sync_engine() -> None:
    """Run the sync engine in a separate thread."""
    from jcselect.sync.engine import sync_engine
    from jcselect.utils.settings import sync_settings

    if not sync_settings.sync_enabled:
        print("Sync engine disabled in settings")
        return

    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Start sync engine
        loop.run_until_complete(sync_engine.start())
        print("Sync engine started successfully")

        # Keep the loop running until the application exits
        loop.run_forever()
    except Exception as e:
        print(f"Sync engine error: {e}")
    finally:
        # Clean shutdown
        if not loop.is_closed():
            loop.run_until_complete(sync_engine.stop())
            loop.close()


def main() -> int:
    """Initialize and run the jcselect application."""
    # Configure logging with performance monitoring
    configure_app_logging()

    # Check application mode and required role from environment
    app_mode = os.environ.get("JCSELECT_MODE", "auto")
    required_role = os.environ.get("JCSELECT_REQUIRED_ROLE", None)

    print(f"🚀 Starting jcselect application (mode: {app_mode}, required_role: {required_role})")

    # Set application properties
    QCoreApplication.setApplicationName("jcselect")
    QCoreApplication.setApplicationVersion("0.1.0")
    QCoreApplication.setOrganizationName("Lebanon Elections")

    app = QGuiApplication(sys.argv)

    # Enable RTL layout for Arabic
    app.setLayoutDirection(Qt.RightToLeft)

    # Register resources (icons, etc.)
    register_resources()

    # Load translations
    translator = QTranslator(app)
    i18n_path = Path(__file__).parent / "i18n"

    # Try to load Arabic (Lebanon) translation
    if translator.load("ar_LB", str(i18n_path)):
        app.installTranslator(translator)
        print("Arabic translation loaded successfully")
    else:
        # Try loading .qm file directly if it exists
        qm_file = i18n_path / "ar_LB.qm"
        if qm_file.exists() and translator.load(str(qm_file)):
            app.installTranslator(translator)
            print("Arabic translation (.qm) loaded successfully")
        else:
            print("Warning: Arabic translation not found, using default English")

    # Start sync engine in daemon thread
    sync_thread = threading.Thread(target=run_sync_engine, daemon=True)
    sync_thread.start()

    # Register QML types
    qmlRegisterType(AppController, "jcselect", 1, 0, "AppController")
    qmlRegisterType(SyncStatusController, "jcselect", 1, 0, "SyncStatusController")
    qmlRegisterType(VoterSearchController, "jcselect", 1, 0, "VoterSearchController")
    qmlRegisterType(TallyController, "jcselect", 1, 0, "TallyController")
    qmlRegisterType(ResultsController, "jcselect", 1, 0, "ResultsController")
    print("✅ Core QML types registered")

    # Register dashboard controllers if available
    if DASHBOARD_AVAILABLE:
        qmlRegisterType(DashboardController, "jcselect", 1, 0, "DashboardController")
        qmlRegisterType(LoginController, "jcselect", 1, 0, "LoginController")
        qmlRegisterType(PenPickerController, "jcselect", 1, 0, "PenPickerController")
        print("✅ Dashboard controllers registered")

    # Create controllers
    app_controller = AppController()
    sync_status_controller = SyncStatusController()
    results_controller = ResultsController()

    # Create dashboard controllers if available
    dashboard_controller = None
    login_controller = None
    if DASHBOARD_AVAILABLE:
        dashboard_controller = DashboardController()
        login_controller = LoginController()

    # Create QML engine
    engine = QQmlApplicationEngine()

    # Expose controllers to QML
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty("syncStatus", sync_status_controller)
    engine.rootContext().setContextProperty("resultsController", results_controller)

    # Expose sync engine to QML for progress monitoring
    from jcselect.sync.engine import get_sync_engine
    sync_engine = get_sync_engine()
    if sync_engine:
        # Connect sync signals for debugging/monitoring
        # Note: Use sync_status_controller for Qt signals, not raw sync engine
        logger.info("Sync engine available for QML integration")

        engine.rootContext().setContextProperty("syncEngine", sync_status_controller)
        print("✅ Sync status controller exposed to QML as syncEngine")
    else:
        engine.rootContext().setContextProperty("syncEngine", None)
        print("⚠️  No sync engine available for QML")

    # Expose dashboard controllers if available
    if DASHBOARD_AVAILABLE:
        engine.rootContext().setContextProperty("dashboardController", dashboard_controller)
        engine.rootContext().setContextProperty("loginController", login_controller)

    # Expose application mode and required role to QML
    engine.rootContext().setContextProperty("appMode", app_mode)
    engine.rootContext().setContextProperty("requiredRole", required_role)
    engine.rootContext().setContextProperty("dashboardAvailable", DASHBOARD_AVAILABLE)

    # Set QML import paths
    src_path = Path(__file__).parent.parent  # Points to src directory
    engine.addImportPath(str(src_path))  # This allows jcselect.ui and jcselect.components to be found

    # Load main QML file
    ui_path = Path(__file__).parent / "ui"
    qml_file = ui_path / "App.qml"
    engine.load(qml_file)

    if not engine.rootObjects():
        print("❌ Failed to load QML - no root objects created")
        return 1

    print(f"✅ Application loaded successfully in {app_mode} mode")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
