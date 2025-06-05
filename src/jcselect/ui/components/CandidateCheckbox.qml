import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: root
    
    property var candidateData: null
    property bool checked: false
    
    signal toggled(string candidateId, bool isChecked)
    
    height: 56
    color: mouseArea.containsMouse ? "#f5f5f5" : "transparent"
    radius: 4
    border.color: root.checked ? Theme.primaryColor : "transparent"
    border.width: root.checked ? 2 : 0
    
    Behavior on color {
        ColorAnimation { duration: 150 }
    }
    
    Behavior on border.color {
        ColorAnimation { duration: 150 }
    }
    
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        
        onClicked: {
            var newChecked = !root.checked
            root.toggled(root.candidateData.id, newChecked)
        }
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12
        
        // Checkbox
        Rectangle {
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            radius: 4
            color: root.checked ? Theme.primaryColor : "white"
            border.color: root.checked ? Theme.primaryColor : "#bdbdbd"
            border.width: 2
            
            Text {
                anchors.centerIn: parent
                text: "✓"
                color: "white"
                font.pixelSize: 14
                font.weight: Font.Bold
                visible: root.checked
            }
        }
        
        // Candidate info
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            
            Text {
                text: root.candidateData ? root.candidateData.name : ""
                font.pixelSize: 14
                font.weight: Font.Medium
                color: "#212121"
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            
            Text {
                text: root.candidateData ? "Order: " + root.candidateData.order : ""
                font.pixelSize: 12
                color: "#757575"
                visible: root.candidateData && root.candidateData.order
            }
        }
        
        // Optional photo placeholder
        Rectangle {
            Layout.preferredWidth: 40
            Layout.preferredHeight: 40
            radius: 20
            color: "#e0e0e0"
            visible: root.candidateData && root.candidateData.photoUrl
            
            Text {
                anchors.centerIn: parent
                text: root.candidateData && root.candidateData.name ? 
                      root.candidateData.name.charAt(0).toUpperCase() : ""
                font.pixelSize: 16
                font.weight: Font.Bold
                color: "#757575"
            }
        }
    }
} 