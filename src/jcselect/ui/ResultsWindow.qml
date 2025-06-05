import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui.components 1.0
import "pages/"

ApplicationWindow {
    id: root
    
    width: 1200
    height: 800
    title: qsTr("النتائج المباشرة - JCSELECT")
    
    color: Theme.backgroundColor
    
    // Results controller instance
    property var resultsController: null
    
    // Refresh data when window becomes visible
    onVisibilityChanged: {
        if (visible && resultsController) {
            resultsController.refreshData()
        }
    }
    
    // Clear new results flag when data is refreshed
    Connections {
        target: resultsController
        function onDataRefreshed() {
            if (resultsController && resultsController.hasNewResults) {
                resultsController.hasNewResults = false
            }
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        
        // Header Row
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: Theme.primaryColor
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing
                spacing: Theme.spacing
                
                Text {
                    text: qsTr("النتائج المباشرة")
                    font.pixelSize: Theme.headlineMedium
                    font.weight: Font.Bold
                    color: "white"
                    Layout.fillWidth: true
                    
                    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
                }
                
                PenSelector {
                    id: penSelector
                    Layout.preferredWidth: 200
                    
                    // Connect to controller
                    onPenSelected: function(penId) {
                        if (resultsController && typeof resultsController.setPenFilter === 'function') {
                            resultsController.setPenFilter(penId)
                        }
                    }
                }
                
                RefreshBadge {
                    id: refreshBadge
                    
                    isSyncing: resultsController ? resultsController.isSyncing : false
                    lastUpdated: resultsController ? resultsController.lastUpdated : new Date()
                    
                    onRefreshRequested: {
                        if (resultsController && typeof resultsController.refreshNow === 'function') {
                            resultsController.refreshNow()
                        }
                    }
                }
                
                ExportMenu {
                    id: exportMenu
                    
                    resultsController: root.resultsController
                    isExporting: resultsController ? resultsController.isExporting : false
                }
            }
        }
        
        // Tab Navigation
        TabBar {
            id: tabBar
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            
            background: Rectangle {
                color: Theme.elevation1
                
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.elevation2
                }
            }
            
            TabButton {
                text: qsTr("إجمالي الأحزاب")
                font.pixelSize: Theme.bodySize
                
                background: Rectangle {
                    color: parent.checked ? Theme.primaryContainer : "transparent"
                    radius: Theme.radius
                    
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        color: Theme.primaryColor
                        visible: parent.parent.checked
                    }
                }
                
                LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
            }
            
            TabButton {
                text: qsTr("نتائج المرشحين")
                font.pixelSize: Theme.bodySize
                
                background: Rectangle {
                    color: parent.checked ? Theme.primaryContainer : "transparent"
                    radius: Theme.radius
                    
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        color: Theme.primaryColor
                        visible: parent.parent.checked
                    }
                }
                
                LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
            }
            
            TabButton {
                text: qsTr("الفائزون")
                font.pixelSize: Theme.bodySize
                
                background: Rectangle {
                    color: parent.checked ? Theme.primaryContainer : "transparent"
                    radius: Theme.radius
                    
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        color: Theme.primaryColor
                        visible: parent.parent.checked
                    }
                }
                
                LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
            }
            
            TabButton {
                text: qsTr("الرسوم البيانية")
                font.pixelSize: Theme.bodySize
                
                background: Rectangle {
                    color: parent.checked ? Theme.primaryContainer : "transparent"
                    radius: Theme.radius
                    
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        color: Theme.primaryColor
                        visible: parent.parent.checked
                    }
                }
                
                LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
            }
        }
        
        // Content Area
        StackLayout {
            id: stackLayout
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            currentIndex: tabBar.currentIndex
            
            PartyTotalsPage {
                id: partyTotalsPage
                visible: stackLayout.currentIndex === 0
                
                onSortRequested: function(columnKey, descending) {
                    // TODO: Connect to controller sort method
                }
            }
            
            CandidateTotalsPage {
                id: candidateTotalsPage
                visible: stackLayout.currentIndex === 1
                
                onSortRequested: function(columnKey, descending) {
                    // TODO: Connect to controller sort method
                }
            }
            
            WinnersPage {
                id: winnersPage
                visible: stackLayout.currentIndex === 2
            }
            
            ChartsPage {
                id: chartsPage
                visible: stackLayout.currentIndex === 3
            }
        }
    }
    
    // Floating Live Sync chip
    Rectangle {
        id: liveSyncChip
        
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 100
        
        width: 120
        height: 40
        radius: 20
        color: Theme.primaryColor
        border.color: "white"
        border.width: 2
        
        visible: resultsController ? resultsController.isSyncing : false
        
        // Slide in animation
        states: [
            State {
                name: "hidden"
                when: !liveSyncChip.visible
                PropertyChanges {
                    target: liveSyncChip
                    opacity: 0
                    anchors.topMargin: 80
                }
            },
            State {
                name: "visible"
                when: liveSyncChip.visible
                PropertyChanges {
                    target: liveSyncChip
                    opacity: 1
                    anchors.topMargin: 100
                }
            }
        ]
        
        transitions: [
            Transition {
                from: "hidden"
                to: "visible"
                ParallelAnimation {
                    NumberAnimation {
                        property: "opacity"
                        duration: Theme.animationDurationMedium
                        easing.type: Theme.animationEasingEmphasized
                    }
                    NumberAnimation {
                        property: "anchors.topMargin"
                        duration: Theme.animationDurationMedium
                        easing.type: Theme.animationEasingEmphasized
                    }
                }
            },
            Transition {
                from: "visible"
                to: "hidden"
                ParallelAnimation {
                    NumberAnimation {
                        property: "opacity"
                        duration: Theme.animationDurationShort
                        easing.type: Theme.animationEasingStandard
                    }
                    NumberAnimation {
                        property: "anchors.topMargin"
                        duration: Theme.animationDurationShort
                        easing.type: Theme.animationEasingStandard
                    }
                }
            }
        ]
        
        RowLayout {
            anchors.centerIn: parent
            spacing: Theme.spacingSmall
            
            BusyIndicator {
                Layout.preferredWidth: 16
                Layout.preferredHeight: 16
                running: parent.parent.visible
            }
            
            Text {
                text: qsTr("مزامنة")
                font.pixelSize: Theme.captionSize
                font.weight: Font.Medium
                color: "white"
                
                LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
            }
        }
    }
    
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
} 