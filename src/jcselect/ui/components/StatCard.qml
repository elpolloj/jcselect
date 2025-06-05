import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Effects
import jcselect.ui 1.0
import jcselect.ui.components 1.0

Rectangle {
    id: root
    
    property string title: ""
    property int value: 0
    property string subtitle: ""
    property string iconSource: ""
    property color accentColor: Theme.primary
    property bool loading: false
    
    height: 120
    radius: 12
    color: Theme.surface
    border.color: root.accentColor
    border.width: 2
    
    // Drop shadow
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: "#0F000000"
        shadowBlur: 0.1
        shadowVerticalOffset: 2
        shadowHorizontalOffset: 0
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16
        
        // Icon
        Rectangle {
            Layout.preferredWidth: 48
            Layout.preferredHeight: 48
            radius: 24
            color: root.accentColor
            
            SvgIcon {
                anchors.centerIn: parent
                source: root.iconSource
                iconSize: 24
                color: Theme.onPrimary
            }
        }
        
        // Text Content
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            
            // Value text or skeleton
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                radius: 4
                color: root.loading ? Theme.surfaceVariant : "transparent"
                visible: root.loading
                
                // Shimmer animation for loading
                Rectangle {
                    anchors.fill: parent
                    radius: 4
                    color: "transparent"
                    
                    Rectangle {
                        id: shimmer
                        width: parent.width * 0.5
                        height: parent.height
                        x: -width
                        color: Qt.rgba(1, 1, 1, 0.3)
                        radius: parent.radius
                        
                        PropertyAnimation on x {
                            running: root.loading
                            loops: Animation.Infinite
                            from: -shimmer.width
                            to: parent.width
                            duration: 1500
                            easing.type: Easing.InOutSine
                        }
                    }
                }
            }
            
            Text {
                text: root.value.toLocaleString()
                font: Theme.headlineMediumFont
                color: Theme.onSurface
                visible: !root.loading
            }

            // Title text or skeleton
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 20
                radius: 4
                color: root.loading ? Theme.surfaceVariant : "transparent"
                visible: root.loading
                opacity: 0.7
            }
            
            Text {
                text: root.title
                font: Theme.titleMediumFont
                color: Theme.onSurface
                visible: !root.loading
            }

            // Subtitle text or skeleton
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 16
                radius: 4
                color: root.loading ? Theme.surfaceVariant : "transparent"
                visible: root.loading
                opacity: 0.5
            }

            Text {
                text: root.subtitle
                font: Theme.bodyMediumFont
                color: Theme.onSurfaceVariant
                visible: !root.loading
            }
        }
    }
} 