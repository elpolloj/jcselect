import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: root
    
    property var warnings: []
    
    visible: warnings.length > 0
    color: "#fff3cd"
    border.color: "#ffc107"
    border.width: 1
    radius: 6
    
    // Animate in/out
    opacity: visible ? 1.0 : 0.0
    Behavior on opacity {
        NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12
        
        // Warning icon
        Rectangle {
            Layout.preferredWidth: 24
            Layout.preferredHeight: 24
            radius: 12
            color: "#ff9800"
            
            Text {
                anchors.centerIn: parent
                text: "⚠"
                font.pixelSize: 16
                color: "white"
                font.weight: Font.Bold
            }
        }
        
        // Warning messages
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            
            Text {
                text: "تحذيرات التصويت" // "Voting Warnings" in Arabic
                font.pixelSize: 14
                font.weight: Font.Bold
                color: "#856404"
                Layout.fillWidth: true
            }
            
            Repeater {
                model: root.warnings
                
                Text {
                    text: "• " + modelData
                    font.pixelSize: 13
                    color: "#856404"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    
                    // RTL support for Arabic text
                    horizontalAlignment: modelData.match(/[\u0600-\u06FF]/) ? 
                                       Text.AlignRight : Text.AlignLeft
                }
            }
        }
        
        // Dismiss button (optional)
        Button {
            Layout.preferredWidth: 30
            Layout.preferredHeight: 30
            
            background: Rectangle {
                radius: 15
                color: parent.hovered ? "#ffc107" : "transparent"
                border.color: "#ffc107"
                border.width: 1
                
                Behavior on color {
                    ColorAnimation { duration: 150 }
                }
            }
            
            contentItem: Text {
                text: "×"
                font.pixelSize: 16
                font.weight: Font.Bold
                color: "#856404"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            
            onClicked: {
                // This would clear warnings - but they should auto-clear 
                // when the validation condition changes
                root.warnings = []
            }
            
            ToolTip.visible: hovered
            ToolTip.text: "إخفاء التحذيرات" // "Hide warnings"
        }
    }
    
    // Subtle pulsing animation for attention
    SequentialAnimation {
        running: root.visible
        loops: Animation.Infinite
        
        PropertyAnimation {
            target: root
            property: "border.width"
            from: 1
            to: 2
            duration: 1500
            easing.type: Easing.InOutSine
        }
        
        PropertyAnimation {
            target: root
            property: "border.width"
            from: 2
            to: 1
            duration: 1500
            easing.type: Easing.InOutSine
        }
    }
} 