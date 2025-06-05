#!/usr/bin/env python3
"""Demo script to test the LoginWindow component."""

import sys
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType


class MockLoginController(QObject):
    """Mock login controller for testing."""
    
    # Signals
    loginSuccessful = Signal('QVariant')
    loginFailed = Signal(str)
    penSelectionRequired = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.login_attempts = 0
    
    @Slot(str, str, bool)
    def authenticate(self, username: str, password: str, remember_me: bool):
        """Mock authentication method."""
        self.login_attempts += 1
        print(f"🔑 Mock login attempt #{self.login_attempts}")
        print(f"   Username: {username}")
        print(f"   Password: {'*' * len(password)}")
        print(f"   Remember me: {remember_me}")
        
        # Simulate different login scenarios
        if username == "admin" and password == "admin":
            print("   ✅ Admin login successful")
            user_info = {
                "user_id": "admin_user",
                "username": "admin", 
                "full_name": "Administrator",
                "role": "admin"
            }
            self.loginSuccessful.emit(user_info)
        elif username == "operator" and password == "operator":
            print("   ✅ Operator login successful")
            user_info = {
                "user_id": "operator_user", 
                "username": "operator",
                "full_name": "Operator", 
                "role": "operator"
            }
            self.loginSuccessful.emit(user_info)
        elif username == "demo" and password == "demo":
            print("   ⚠️  Pen selection required")
            user_info = {
                "user_id": "demo_user",
                "username": "demo",
                "full_name": "Demo User",
                "role": "operator"
            }
            self.penSelectionRequired.emit()
        else:
            print("   ❌ Login failed")
            self.loginFailed.emit("Invalid username or password")


def main():
    """Run the login window demo."""
    print("🗳️  jcselect LoginWindow Demo")
    print("=" * 50)
    print("Test credentials:")
    print("  admin/admin     - Admin login")
    print("  operator/operator - Operator login") 
    print("  demo/demo       - Pen selection required")
    print("  anything else   - Login failure")
    print("=" * 50)
    
    # Set application properties
    QCoreApplication.setApplicationName("jcselect-login-demo")
    QCoreApplication.setApplicationVersion("0.1.0")
    
    app = QGuiApplication(sys.argv)
    
    # Register mock controller
    qmlRegisterType(MockLoginController, "jcselect", 1, 0, "MockLoginController")
    
    # Create QML engine
    engine = QQmlApplicationEngine()
    
    # Set QML import paths
    src_path = Path(__file__).parent / "src"
    engine.addImportPath(str(src_path))
    
    # Expose app mode for testing
    engine.rootContext().setContextProperty("appMode", "demo")
    
    # Load demo QML file
    demo_qml = """
import QtQuick 2.15
import QtQuick.Controls 2.15
import jcselect.ui 1.0
import jcselect 1.0

ApplicationWindow {
    id: window
    width: 1000
    height: 700
    visible: true
    title: "jcselect LoginWindow Demo"
    
    MockLoginController {
        id: mockController
        
        onLoginSuccessful: function(userInfo) {
            console.log("Login successful for:", userInfo.username, "role:", userInfo.role)
            successDialog.userInfo = userInfo
            successDialog.open()
        }
        
        onLoginFailed: function(errorMessage) {
            console.log("Login failed:", errorMessage)
        }
        
        onPenSelectionRequired: function() {
            console.log("Pen selection required")
            penDialog.open()
        }
    }
    
    LoginWindow {
        anchors.fill: parent
        loginController: mockController
    }
    
    Dialog {
        id: successDialog
        title: "Login Successful"
        modal: true
        anchors.centerIn: parent
        
        property var userInfo: null
        
        Column {
            spacing: 10
            
            Text {
                text: "Welcome, " + (successDialog.userInfo ? successDialog.userInfo.full_name : "")
                font.pixelSize: 16
                font.weight: Font.Bold
            }
            
            Text {
                text: "Role: " + (successDialog.userInfo ? successDialog.userInfo.role : "")
                font.pixelSize: 14
            }
            
            Button {
                text: "Close"
                onClicked: successDialog.close()
            }
        }
    }
    
    Dialog {
        id: penDialog
        title: "Pen Selection Required"
        modal: true
        anchors.centerIn: parent
        
        Column {
            spacing: 10
            
            Text {
                text: "This user requires pen selection."
                font.pixelSize: 14
            }
            
            Text {
                text: "(In real app, PenPickerDialog would show here)"
                font.pixelSize: 12
                opacity: 0.7
            }
            
            Button {
                text: "Close"
                onClicked: penDialog.close()
            }
        }
    }
}
"""
    
    # Write demo QML to temporary file
    demo_file = Path("temp_login_demo.qml")
    demo_file.write_text(demo_qml)
    
    try:
        # Load the demo
        engine.load(demo_file)
        
        if not engine.rootObjects():
            print("❌ Failed to load demo QML")
            return 1
        
        print("✅ LoginWindow demo loaded successfully!")
        return app.exec()
        
    finally:
        # Clean up temp file
        if demo_file.exists():
            demo_file.unlink()


if __name__ == "__main__":
    sys.exit(main()) 