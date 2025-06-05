import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

RowLayout {
    id: root
    
    property bool isSyncing: false
    property date lastUpdated: new Date()
    property bool hasError: false
    
    signal refreshRequested()
    
    spacing: Theme.spacingSmall
    
    // Calculate time since last update in seconds
    readonly property int secondsSinceUpdate: Math.floor((new Date() - lastUpdated) / 1000)
    
    // Determine status color based on time elapsed
    readonly property color statusColor: {
        if (hasError) return Theme.errorColor
        if (secondsSinceUpdate < 20) return Theme.successColor
        if (secondsSinceUpdate < 120) return Theme.warningColor
        return Theme.errorColor
    }
    
    // Status indicator with spinning animation when syncing
    Rectangle {
        id: statusIndicator
        Layout.preferredWidth: 24
        Layout.preferredHeight: 24
        radius: 12
        color: statusColor
        
        // Spinning sync icon
        Text {
            anchors.centerIn: parent
            text: isSyncing ? "⟳" : "●"
            font.pixelSize: isSyncing ? 14 : 8
            color: "white"
            
            RotationAnimation on rotation {
                running: isSyncing
                loops: Animation.Infinite
                duration: 1000
                from: 0
                to: 360
            }
        }
        
        // Subtle pulsing when syncing
        SequentialAnimation on opacity {
            running: isSyncing
            loops: Animation.Infinite
            NumberAnimation { from: 1.0; to: 0.6; duration: 500 }
            NumberAnimation { from: 0.6; to: 1.0; duration: 500 }
        }
    }
    
    // Status text with Arabic timestamp
    Column {
        Layout.fillWidth: true
        spacing: 2
        
        Text {
            id: statusText
            text: {
                if (isSyncing) return qsTr("جاري التحديث...")
                if (hasError) return qsTr("خطأ في التحديث")
                return qsTr("متصل")
            }
            font.pixelSize: Theme.bodySize
            color: Theme.textColor
            font.weight: Font.Medium
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
        
        Text {
            id: timestampText
            text: qsTr("آخر تحديث: ") + Qt.formatTime(lastUpdated, "hh:mm:ss")
            font.pixelSize: Theme.captionSize
            color: Theme.textColor
            opacity: 0.7
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
    }
    
    // Manual refresh button
    Button {
        id: refreshButton
        Layout.preferredWidth: 36
        Layout.preferredHeight: 36
        
        enabled: !isSyncing
        
        contentItem: Text {
            text: "↻"
            font.pixelSize: 16
            color: refreshButton.enabled ? Theme.primaryColor : Theme.textColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            opacity: refreshButton.enabled ? 1.0 : 0.5
        }
        
        background: Rectangle {
            color: refreshButton.pressed ? Theme.elevation2 : 
                   refreshButton.hovered ? Theme.elevation1 : "transparent"
            radius: Theme.radius
            border.color: refreshButton.activeFocus ? Theme.primaryColor : "transparent"
            border.width: 1
        }
        
        onClicked: refreshRequested()
        
        ToolTip.visible: hovered
        ToolTip.text: qsTr("تحديث يدوي")
        ToolTip.delay: 500
    }
    
    // Timer to update the timestamp display every second
    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            // Force re-evaluation of bindings
            root.secondsSinceUpdate = Math.floor((new Date() - root.lastUpdated) / 1000)
        }
    }
    
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
} 