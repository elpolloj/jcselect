import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: root
    
    property int totalVotes: 0
    property int totalCounted: 0
    property int totalCandidates: 0
    property int totalWhite: 0
    property int totalIllegal: 0
    property int totalCancel: 0
    property int totalBlank: 0
    
    color: "#e8f5e8"
    radius: 8
    border.color: "#4caf50"
    border.width: 1
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        
        // Header
        Text {
            text: "إجمالي الأصوات" // "Vote Totals" in Arabic
            font.pixelSize: 18
            font.weight: Font.Bold
            color: "#2e7d32"
            Layout.alignment: Qt.AlignHCenter
        }
        
        // Main totals grid
        GridLayout {
            Layout.fillWidth: true
            columns: 4
            rowSpacing: 8
            columnSpacing: 16
            
            // Total votes
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                color: "#1976d2"
                radius: 6
                
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    
                    Text {
                        text: root.totalVotes
                        font.pixelSize: 24
                        font.weight: Font.Bold
                        color: "white"
                        Layout.alignment: Qt.AlignHCenter
                    }
                    
                    Text {
                        text: "مجموع الأصوات" // "Total Votes"
                        font.pixelSize: 12
                        color: "white"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
            
            // Candidate votes
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                color: "#388e3c"
                radius: 6
                
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    
                    Text {
                        text: root.totalCandidates
                        font.pixelSize: 24
                        font.weight: Font.Bold
                        color: "white"
                        Layout.alignment: Qt.AlignHCenter
                    }
                    
                    Text {
                        text: "أصوات المرشحين" // "Candidate Votes"
                        font.pixelSize: 12
                        color: "white"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
            
            // White ballots
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                color: "#f57c00"
                radius: 6
                
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    
                    Text {
                        text: root.totalWhite
                        font.pixelSize: 24
                        font.weight: Font.Bold
                        color: "white"
                        Layout.alignment: Qt.AlignHCenter
                    }
                    
                    Text {
                        text: "بيضاء" // "White"
                        font.pixelSize: 12
                        color: "white"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
            
            // Illegal ballots
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                color: "#d32f2f"
                radius: 6
                
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    
                    Text {
                        text: root.totalIllegal
                        font.pixelSize: 24
                        font.weight: Font.Bold
                        color: "white"
                        Layout.alignment: Qt.AlignHCenter
                    }
                    
                    Text {
                        text: "باطلة" // "Invalid"
                        font.pixelSize: 12
                        color: "white"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }
        
        // Secondary totals
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            
            // Cancel ballots
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                color: "#757575"
                radius: 4
                
                RowLayout {
                    anchors.centerIn: parent
                    spacing: 8
                    
                    Text {
                        text: root.totalCancel
                        font.pixelSize: 16
                        font.weight: Font.Bold
                        color: "white"
                    }
                    
                    Text {
                        text: "ملغاة" // "Cancelled"
                        font.pixelSize: 12
                        color: "white"
                    }
                }
            }
            
            // Blank ballots
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                color: "#9e9e9e"
                radius: 4
                
                RowLayout {
                    anchors.centerIn: parent
                    spacing: 8
                    
                    Text {
                        text: root.totalBlank
                        font.pixelSize: 16
                        font.weight: Font.Bold
                        color: "white"
                    }
                    
                    Text {
                        text: "فارغة" // "Blank"
                        font.pixelSize: 12
                        color: "white"
                    }
                }
            }
            
            // Counted total
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                color: "#5d4037"
                radius: 4
                
                RowLayout {
                    anchors.centerIn: parent
                    spacing: 8
                    
                    Text {
                        text: root.totalCounted
                        font.pixelSize: 16
                        font.weight: Font.Bold
                        color: "white"
                    }
                    
                    Text {
                        text: "مفروزة" // "Counted"
                        font.pixelSize: 12
                        color: "white"
                    }
                }
            }
        }
    }
    
    // Smooth animations for count changes
    Behavior on totalVotes {
        NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
    }
    
    Behavior on totalCandidates {
        NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
    }
    
    Behavior on totalWhite {
        NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
    }
    
    Behavior on totalIllegal {
        NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
    }
} 