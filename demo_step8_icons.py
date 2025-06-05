#!/usr/bin/env python3
"""Demo script to test icon loading in Step 8."""

import sys
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QResource
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine


def main():
    """Test icon loading demo."""
    print("🗳️  Step 8 Icons Demo")
    print("=" * 50)
    
    # Set application properties
    QCoreApplication.setApplicationName("jcselect-icons-demo")
    QCoreApplication.setApplicationVersion("0.1.0")
    
    app = QGuiApplication(sys.argv)
    
    # Register resources
    resources_path = Path("src/jcselect/resources")
    if resources_path.exists():
        QResource.addSearchPath(str(resources_path))
        print("✅ Resources path registered")
    
    # Test icon loading
    icons_to_test = [
        "search-voters.svg",
        "tally-count.svg", 
        "turnout-stats.svg",
        "results-charts.svg",
        "winners.svg",
        "count-ops.svg",
        "setup.svg",
        "system-settings.svg",
        "test.svg"
    ]
    
    print("\n📱 Testing Icon Loading:")
    all_icons_ok = True
    
    for icon_name in icons_to_test:
        # Test file existence
        icon_file = Path(f"src/jcselect/resources/icons/{icon_name}")
        file_exists = icon_file.exists()
        
        # Test QIcon loading
        qicon = QIcon(f"qrc:/icons/{icon_name}")
        icon_loaded = not qicon.isNull() if file_exists else False
        
        status = "✅" if file_exists else "❌"
        print(f"  {status} {icon_name:<20} {'(file exists)' if file_exists else '(missing)'}")
        
        if not file_exists:
            all_icons_ok = False
    
    # Create QML engine for full test
    engine = QQmlApplicationEngine()
    
    # Set QML import paths
    src_path = Path("src")
    engine.addImportPath(str(src_path))
    
    # Load demo QML with CardTile
    demo_qml = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0
import jcselect.components 1.0

ApplicationWindow {{
    id: window
    width: 800
    height: 600
    visible: true
    title: "Icon Loading Demo"
    
    ScrollView {{
        anchors.fill: parent
        anchors.margins: 20
        
        GridLayout {{
            columns: 3
            rowSpacing: 20
            columnSpacing: 20
            
            {chr(10).join([f'''
            CardTile {{
                width: 200
                height: 160
                title: "{icon_name.replace('-', ' ').title()}"
                subtitle: "Test icon loading"
                iconSource: "qrc:/icons/{icon_name}"
                onClicked: console.log("Clicked {icon_name}")
            }}''' for icon_name in icons_to_test[:9]])}
        }}
    }}
}}
"""
    
    # Write demo QML to temporary file
    demo_file = Path("temp_icons_demo.qml")
    demo_file.write_text(demo_qml)
    
    try:
        # Load the demo
        engine.load(demo_file)
        
        if not engine.rootObjects():
            print("❌ Failed to load demo QML")
            return 1
        
        print(f"\n✅ Icons demo loaded successfully!")
        print("💡 You should see icon tiles in the window.")
        print("💡 Icons that display correctly have loaded properly.")
        print("💡 Close the window to exit.")
        return app.exec()
        
    finally:
        # Clean up temp file
        if demo_file.exists():
            demo_file.unlink()


if __name__ == "__main__":
    sys.exit(main()) 