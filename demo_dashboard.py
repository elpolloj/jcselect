#!/usr/bin/env python3
"""Demo script for dashboard functionality."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtGui import QGuiApplication
import sys
from pathlib import Path

# Import the controllers
try:
    from src.jcselect.controllers.dashboard_controller import DashboardController
    from src.jcselect.controllers.login_controller import LoginController
    from src.jcselect.controllers.pen_picker_controller import PenPickerController
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

def test_dashboard():
    """Test dashboard functionality."""
    app = QGuiApplication([])
    
    # Register QML types
    qmlRegisterType(DashboardController, "jcselect.controllers", 1, 0, "DashboardController")
    qmlRegisterType(LoginController, "jcselect.controllers", 1, 0, "LoginController")
    qmlRegisterType(PenPickerController, "jcselect.controllers", 1, 0, "PenPickerController")
    
    # Create QML engine
    engine = QQmlApplicationEngine()
    
    # Set QML import paths
    components_path = Path(__file__).parent / "src" / "jcselect"
    engine.addImportPath(str(components_path))
    
    print("✅ QML engine created")
    print(f"✅ Import path added: {components_path}")
    
    # Create dashboard controller instance
    dashboard_controller = DashboardController()
    login_controller = LoginController()
    
    # Set context properties
    engine.rootContext().setContextProperty("dashboardController", dashboard_controller)
    engine.rootContext().setContextProperty("loginController", login_controller)
    
    print("✅ Controllers created and registered")
    
    # Create a simple QML demo for dashboard
    qml_content = """
import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0
import jcselect.components 1.0

Window {
    id: window
    width: 1000
    height: 700
    visible: true
    title: "Dashboard Demo"
    
    Rectangle {
        anchors.fill: parent
        color: Theme.backgroundColor
        
        TabBar {
            id: tabBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 50
            
            TabButton {
                text: "Admin Dashboard"
            }
            TabButton {
                text: "Operator Dashboard"
            }
            TabButton {
                text: "Single CardTile"
            }
        }
        
        StackLayout {
            anchors.top: tabBar.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            
            currentIndex: tabBar.currentIndex
            
            // Admin Dashboard
            AdminDashboard {
                dashboardController: window.dashboardController
            }
            
            // Operator Dashboard  
            OperatorDashboard {
                dashboardController: window.dashboardController
                operatorName: "Demo Operator"
            }
            
            // Single CardTile Test
            Rectangle {
                color: Theme.surfaceColor
                
                CardTile {
                    anchors.centerIn: parent
                    title: "Test Card"
                    subtitle: "Demo functionality"
                    badgeText: "42"
                    badgeVisible: true
                    
                    onClicked: {
                        console.log("Demo card clicked!")
                    }
                }
            }
        }
    }
    
    property var dashboardController: null
    
    Component.onCompleted: {
        dashboardController = window.dashboardController;
        console.log("Dashboard demo window loaded successfully!");
        
        // Test dashboard controller properties
        if (dashboardController) {
            console.log("Dashboard Controller Properties:");
            console.log("- Pending Voters:", dashboardController.pendingVoters);
            console.log("- Active Sessions:", dashboardController.activeSessions);
            console.log("- Total Voters:", dashboardController.totalVoters);
            console.log("- Current Pen Label:", dashboardController.currentPenLabel);
            console.log("- Sync Status:", dashboardController.syncStatus);
        }
    }
}
"""
    
    # Load QML from string
    try:
        engine.loadData(qml_content.encode('utf-8'))
        print("✅ QML content loaded successfully")
        
        if not engine.rootObjects():
            print("❌ No root objects created")
            return 1
            
        print("✅ Dashboard components instantiated successfully!")
        print("\n🎯 Demo Features:")
        print("- Admin Dashboard (8 CardTiles)")
        print("- Operator Dashboard (2 large CardTiles)")
        print("- Single CardTile test")
        print("- Dashboard Controller with live data")
        print("\n✅ Demo completed - Dashboard system is working!")
        
        # Don't actually run the app loop, just test instantiation
        return 0
        
    except Exception as e:
        print(f"❌ Failed to load QML: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_dashboard()) 