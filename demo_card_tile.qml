import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Layouts 1.15
import jcselect.components 1.0

Window {
    id: window
    width: 800
    height: 600
    visible: true
    title: "CardTile Component Demo"
    color: "#f5f5f5"

    ScrollView {
        anchors.fill: parent
        anchors.margins: 20

        GridLayout {
            width: parent.width
            columns: 3
            rowSpacing: 20
            columnSpacing: 20

            // Basic card
            CardTile {
                title: "Voter Search"
                subtitle: "Search & check-in voters"
                onClicked: console.log("Voter Search clicked")
            }

            // Card with badge
            CardTile {
                title: "Vote Counting"
                subtitle: "Record vote tallies"
                badgeText: "5"
                badgeVisible: true
                badgeColor: "#FF9800"
                onClicked: console.log("Vote Counting clicked")
            }

            // Card with error badge
            CardTile {
                title: "Turnout Reports"
                subtitle: "Voting statistics"
                badgeText: "!"
                badgeVisible: true
                badgeColor: "#F44336"
                onClicked: console.log("Turnout Reports clicked")
            }

            // Disabled card
            CardTile {
                title: "Results Charts"
                subtitle: "Bershaan & Flaan analysis"
                enabled: false
                onClicked: console.log("Results Charts clicked (should not fire)")
            }

            // Card with longer text
            CardTile {
                title: "Lebanese Tally Management System"
                subtitle: "Complete election management with real-time synchronization"
                badgeText: "12"
                badgeVisible: true
                onClicked: console.log("Long title card clicked")
            }

            // Success badge card
            CardTile {
                title: "System Settings"
                subtitle: "App configuration"
                badgeText: "✓"
                badgeVisible: true
                badgeColor: "#4CAF50"
                onClicked: console.log("System Settings clicked")
                onRightClicked: console.log("System Settings right-clicked")
            }

            // Large badge number
            CardTile {
                title: "Pending Actions"
                subtitle: "Items requiring attention"
                badgeText: "999+"
                badgeVisible: true
                badgeColor: "#9C27B0"
                onClicked: console.log("Pending Actions clicked")
            }

            // Minimal card
            CardTile {
                title: "Setup"
                onClicked: console.log("Setup clicked")
            }

            // Card with very long subtitle for wrapping test
            CardTile {
                title: "Data Export"
                subtitle: "Export all election data including voter information, tally results, and audit logs to various formats"
                onClicked: console.log("Data Export clicked")
            }
        }
    }

    // Instructions
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        color: "#2196F3"
        opacity: 0.9

        Text {
            anchors.centerIn: parent
            text: "CardTile Demo - Click cards to see console output, try keyboard navigation (Tab/Enter/Space), and right-click for context menus"
            color: "white"
            font.pixelSize: 14
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }
    }
} 