import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: root
    
    property string selectedType: "normal"
    
    signal typeSelected(string ballotType)
    
    color: "white"
    radius: 8
    border.color: "#e0e0e0"
    border.width: 1
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        
        // Header
        Text {
            text: "نوع الورقة" // "Ballot Type" in Arabic
            font.pixelSize: 16
            font.weight: Font.Bold
            color: "#212121"
            Layout.alignment: Qt.AlignHCenter
        }
        
        // Ballot type buttons
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            
            // Normal ballot (for reference, but not selectable here since it's selected via candidates)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                radius: 6
                color: root.selectedType === "normal" ? Theme.primaryColor : "#f5f5f5"
                border.color: root.selectedType === "normal" ? Theme.primaryColor : "#e0e0e0"
                border.width: 1
                
                Text {
                    anchors.centerIn: parent
                    text: "عادي" // "Normal" in Arabic
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    color: root.selectedType === "normal" ? "white" : "#757575"
                }
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.typeSelected("normal")
                }
            }
            
            // Cancel ballot
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                radius: 6
                color: root.selectedType === "cancel" ? "#d32f2f" : "#f5f5f5"
                border.color: root.selectedType === "cancel" ? "#d32f2f" : "#e0e0e0"
                border.width: 1
                
                Text {
                    anchors.centerIn: parent
                    text: "ملغى" // "Cancel/Void" in Arabic
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    color: root.selectedType === "cancel" ? "white" : "#757575"
                }
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.typeSelected("cancel")
                }
            }
            
            // White ballot
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                radius: 6
                color: root.selectedType === "white" ? "#ff9800" : "#f5f5f5"
                border.color: root.selectedType === "white" ? "#ff9800" : "#e0e0e0"
                border.width: 1
                
                Text {
                    anchors.centerIn: parent
                    text: "بيضاء" // "White" in Arabic
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    color: root.selectedType === "white" ? "white" : "#757575"
                }
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.typeSelected("white")
                }
            }
            
            // Illegal ballot
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                radius: 6
                color: root.selectedType === "illegal" ? "#e91e63" : "#f5f5f5"
                border.color: root.selectedType === "illegal" ? "#e91e63" : "#e0e0e0"
                border.width: 1
                
                Text {
                    anchors.centerIn: parent
                    text: "باطل" // "Invalid/Illegal" in Arabic
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    color: root.selectedType === "illegal" ? "white" : "#757575"
                }
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.typeSelected("illegal")
                }
            }
            
            // Blank ballot
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                radius: 6
                color: root.selectedType === "blank" ? "#9e9e9e" : "#f5f5f5"
                border.color: root.selectedType === "blank" ? "#9e9e9e" : "#e0e0e0"
                border.width: 1
                
                Text {
                    anchors.centerIn: parent
                    text: "فارغ" // "Blank" in Arabic
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    color: root.selectedType === "blank" ? "white" : "#757575"
                }
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.typeSelected("blank")
                }
            }
        }
        
        Item { Layout.fillHeight: true }
    }
} 