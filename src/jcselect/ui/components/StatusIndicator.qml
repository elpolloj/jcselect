import QtQuick 2.15
import QtQuick.Controls 2.15
import jcselect.ui 1.0

Item {
    id: root
    width: 16
    height: 16
    
    property bool online: true
    property bool syncing: false
    property string status: online ? (syncing ? "syncing" : "online") : "offline"
    
    Rectangle {
        id: indicator
        anchors.fill: parent
        radius: width / 2
        color: {
            switch(root.status) {
                case "online": return Theme.success
                case "syncing": return Theme.warning  
                case "offline": return Theme.error
                default: return Theme.onSurfaceVariant
            }
        }
        
        // Syncing Animation
        RotationAnimator {
            target: indicator
            running: root.syncing
            from: 0
            to: 360
            duration: 1000
            loops: Animation.Infinite
        }
    }
    
    // Tooltip for status
    ToolTip.text: {
        switch(root.status) {
            case "online": return qsTr("متصل")
            case "syncing": return qsTr("مزامنة جارية...")
            case "offline": return qsTr("غير متصل")
            default: return qsTr("حالة غير معروفة")
        }
    }
    ToolTip.visible: mouseArea.containsMouse
    ToolTip.delay: 500
    
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
    }
} 