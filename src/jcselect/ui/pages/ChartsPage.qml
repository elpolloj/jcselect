import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: root
    
    color: Theme.backgroundColor
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing
        spacing: Theme.spacingLarge
        
        // Page header
        Text {
            text: qsTr("الرسوم البيانية")
            font.pixelSize: Theme.titleLarge
            font.weight: Font.Bold
            color: Theme.textColor
            Layout.fillWidth: true
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
        
        // Placeholder content
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            
            Column {
                anchors.centerIn: parent
                spacing: Theme.spacingLarge
                
                Text {
                    text: "📊"
                    font.pixelSize: 72
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    opacity: 0.5
                }
                
                Text {
                    text: qsTr("قريباً...")
                    font.pixelSize: Theme.headlineMedium
                    font.weight: Font.Bold
                    color: Theme.textColor
                    opacity: 0.7
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                }
                
                Text {
                    text: qsTr("سيتم إضافة الرسوم البيانية في التحديث القادم")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.5
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    wrapMode: Text.WordWrap
                    width: Math.min(400, root.width - Theme.spacing * 2)
                    
                    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                }
                
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 300
                    height: 1
                    color: Theme.elevation2
                    opacity: 0.3
                }
                
                Text {
                    text: qsTr("• مخططات دائرية لتوزيع الأصوات\n• رسوم بيانية لمقارنة الأحزاب\n• تحليل إحصائي متقدم")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.4
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    lineHeight: 1.5
                    
                    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                }
            }
        }
    }
    
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
} 