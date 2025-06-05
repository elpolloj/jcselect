import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0

Item {
    id: root
    
    // Properties
    property string title: ""
    property alias content: contentArea.children
    property alias contentItem: contentArea
    
    // Gradient Title Bar (48px height as specified)
    Rectangle {
        id: headerBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 48
        
        // Gradient background as specified
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.headerGradientStart }
            GradientStop { position: 1.0; color: Theme.headerGradientEnd }
        }
        
        // Title text
        Text {
            anchors.centerIn: parent
            text: root.title
            font: Theme.titleLargeFont
            color: Theme.primaryText
            horizontalAlignment: Text.AlignHCenter
        }
        
        // Bottom shadow line for depth
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: "#0003"  // Semi-transparent black shadow
        }
    }
    
    // Content area below header
    Item {
        id: contentArea
        anchors.top: headerBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        
        // Add top margin for breathing room as specified in layout overhaul
        anchors.topMargin: Theme.margin
    }
} 