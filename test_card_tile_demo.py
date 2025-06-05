#!/usr/bin/env python3
"""Quick demo of CardTile component functionality."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtGui import QGuiApplication
import sys
from pathlib import Path

def test_card_tile():
    """Test basic CardTile component functionality."""
    app = QGuiApplication([])
    
    # Create QML engine
    engine = QQmlApplicationEngine()
    
    # Set QML import paths
    components_path = Path(__file__).parent / "src" / "jcselect"
    engine.addImportPath(str(components_path))
    
    print("✅ QML engine created")
    print(f"✅ Import path added: {components_path}")
    
    # Create a simple QML string to test CardTile
    qml_content = """
import QtQuick 2.15
import QtQuick.Window 2.15
import jcselect.components 1.0

Window {
    id: window
    width: 300
    height: 200
    visible: true
    title: "CardTile Test"
    
    CardTile {
        anchors.centerIn: parent
        title: "Test Card"
        subtitle: "Demo subtitle"
        badgeText: "3"
        badgeVisible: true
        
        onClicked: {
            console.log("CardTile clicked!")
        }
        
        onRightClicked: {
            console.log("CardTile right-clicked!")
        }
    }
    
    Component.onCompleted: {
        console.log("CardTile demo window loaded successfully!")
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
            
        print("✅ CardTile component instantiated successfully!")
        print("✅ Demo completed - CardTile is working!")
        
        # Don't actually run the app loop, just test instantiation
        return 0
        
    except Exception as e:
        print(f"❌ Failed to load QML: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_card_tile()) 