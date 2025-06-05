import QtQuick 2.15
import QtQuick.Controls 2.15
import jcselect.ui 1.0
import QtQuick.Layouts 1.15

Rectangle {
    id: performanceOverlay
    
    property var controller
    property bool debugMode: false
    property bool autoHide: true
    property int hideDelay: 3000 // 3 seconds
    
    // Performance metrics
    property real lastSearchTime: controller ? controller.lastSearchTimeMs : 0
    property real lastMarkTime: controller ? controller.lastMarkTimeMs : 0
    property real avgSearchTime: controller ? controller.avgSearchTimeMs : 0
    property real avgMarkTime: controller ? controller.avgMarkTimeMs : 0
    property int totalSearches: controller ? controller.totalSearches : 0
    property int totalMarks: controller ? controller.totalMarks : 0
    
    width: layout.implicitWidth + Theme.spacingMedium * 2
    height: layout.implicitHeight + Theme.spacingSmall * 2
    radius: Theme.radius
    color: Theme.elevation2
    border.color: Theme.elevation3
    border.width: 1
    
    // Position in top-right corner
    anchors.top: parent.top
    anchors.right: parent.right
    anchors.margins: Theme.spacingMedium
    
    // Auto-hide behavior
    visible: shouldShow
    opacity: shouldShow ? 1.0 : 0.0
    
    property bool shouldShow: {
        if (debugMode) return true
        if (lastSearchTime > 0 || lastMarkTime > 0) return true
        return false
    }
    
    // Auto-hide timer
    Timer {
        id: hideTimer
        interval: hideDelay
        repeat: false
        running: autoHide && shouldShow && !debugMode
        onTriggered: {
            if (!debugMode) {
                // Reset metrics to hide overlay
                if (controller) {
                    // Don't actually reset, just stop showing recent metrics
                }
            }
        }
    }
    
    // Fade animation
    Behavior on opacity {
        NumberAnimation {
            duration: Theme.animationDurationMedium
            easing.type: Theme.animationEasingStandard
        }
    }
    
    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.margins: Theme.spacingSmall
        spacing: Theme.spacingTiny
        
        // Header
        Text {
            Layout.fillWidth: true
            text: "⚡ Performance"
            font.pixelSize: Theme.captionSize
            font.bold: true
            color: Theme.textColor
            horizontalAlignment: Text.AlignCenter
        }
        
        // Separator
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.elevation3
        }
        
        // Search metrics
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingTiny
            visible: lastSearchTime > 0 || totalSearches > 0
            
            Text {
                text: "🔍"
                font.pixelSize: Theme.captionSize
                color: Theme.textColor
            }
            
            Text {
                Layout.fillWidth: true
                text: lastSearchTime > 0 ? `${lastSearchTime.toFixed(1)}ms` : "-"
                font.pixelSize: Theme.captionSize
                color: {
                    if (lastSearchTime === 0) return Qt.darker(Theme.textColor, 1.5)
                    if (lastSearchTime > 200) return Theme.errorColor
                    if (lastSearchTime > 100) return "#FFA500" // Orange
                    return Theme.successColor
                }
                horizontalAlignment: Text.AlignRight
            }
        }
        
        // Mark metrics
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingTiny
            visible: lastMarkTime > 0 || totalMarks > 0
            
            Text {
                text: "✓"
                font.pixelSize: Theme.captionSize
                color: Theme.textColor
            }
            
            Text {
                Layout.fillWidth: true
                text: lastMarkTime > 0 ? `${lastMarkTime.toFixed(1)}ms` : "-"
                font.pixelSize: Theme.captionSize
                color: {
                    if (lastMarkTime === 0) return Qt.darker(Theme.textColor, 1.5)
                    if (lastMarkTime > 500) return Theme.errorColor
                    if (lastMarkTime > 200) return "#FFA500" // Orange
                    return Theme.successColor
                }
                horizontalAlignment: Text.AlignRight
            }
        }
        
        // Average metrics (debug mode only)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: avgLayout.implicitHeight + Theme.spacingTiny
            color: "transparent"
            visible: debugMode && (totalSearches > 1 || totalMarks > 1)
            
            ColumnLayout {
                id: avgLayout
                anchors.fill: parent
                spacing: Theme.spacingTiny
                
                Text {
                    Layout.fillWidth: true
                    text: "Averages"
                    font.pixelSize: Theme.captionSize - 2
                    color: Qt.darker(Theme.textColor, 1.3)
                    horizontalAlignment: Text.AlignCenter
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingTiny
                    visible: totalSearches > 1
                    
                    Text {
                        text: "🔍 avg:"
                        font.pixelSize: Theme.captionSize - 2
                        color: Qt.darker(Theme.textColor, 1.3)
                    }
                    
                    Text {
                        Layout.fillWidth: true
                        text: `${avgSearchTime.toFixed(1)}ms (${totalSearches})`
                        font.pixelSize: Theme.captionSize - 2
                        color: Qt.darker(Theme.textColor, 1.3)
                        horizontalAlignment: Text.AlignRight
                    }
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingTiny
                    visible: totalMarks > 1
                    
                    Text {
                        text: "✓ avg:"
                        font.pixelSize: Theme.captionSize - 2
                        color: Qt.darker(Theme.textColor, 1.3)
                    }
                    
                    Text {
                        Layout.fillWidth: true
                        text: `${avgMarkTime.toFixed(1)}ms (${totalMarks})`
                        font.pixelSize: Theme.captionSize - 2
                        color: Qt.darker(Theme.textColor, 1.3)
                        horizontalAlignment: Text.AlignRight
                    }
                }
            }
        }
        
        // Reset button (debug mode only)
        Button {
            Layout.fillWidth: true
            Layout.preferredHeight: 20
            visible: debugMode
            text: "Reset"
            font.pixelSize: Theme.captionSize - 2
            
            background: Rectangle {
                color: parent.pressed ? Theme.elevation3 : Theme.elevation1
                radius: Theme.spacingTiny
                border.color: Theme.elevation3
                border.width: 1
            }
            
            contentItem: Text {
                text: parent.text
                font: parent.font
                color: Theme.textColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            
            onClicked: {
                if (controller) {
                    controller.resetPerformanceMetrics()
                }
            }
        }
    }
    
    // Update visibility when metrics change
    Connections {
        target: controller
        function onPerformanceMetricChanged() {
            // Restart hide timer when new metrics come in
            if (autoHide && !debugMode) {
                hideTimer.restart()
            }
        }
    }
    
    // Mouse area for interaction
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        
        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                // Toggle debug mode on right-click
                debugMode = !debugMode
            }
        }
        
        onEntered: {
            // Stop auto-hide when hovering
            hideTimer.stop()
        }
        
        onExited: {
            // Resume auto-hide when leaving
            if (autoHide && !debugMode) {
                hideTimer.restart()
            }
        }
    }
    
    // Tooltip for interaction hints
    ToolTip {
        visible: parent.hovered && !debugMode
        text: "Right-click for debug mode"
        delay: 1000
    }
} 