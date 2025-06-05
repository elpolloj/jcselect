import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui 1.0
import jcselect.components 1.0
import jcselect.ui.components 1.0

Rectangle {
    id: root

    // Dashboard controller for navigation and data
    property var dashboardController: null
    property var syncStatusController: null
    property string operatorName: ""
    property var syncEngine: null

    color: Theme.background

    // Replace ScrollView with direct ColumnLayout for no scrolling
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16  // Consistent with AdminDashboard
        spacing: 12

        // Enhanced Header Section - Fixed height
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 60  // Fixed height for header
            spacing: 16

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Text {
                    text: qsTr("لوحة إدارة المشغل")
                    font: Theme.headlineLargeFont
                    color: Theme.onBackground
                }

                RowLayout {
                    spacing: 8

                    StatusIndicator {
                        online: dashboardController ? dashboardController.isOnline : false
                        syncing: dashboardController ? dashboardController.isSyncing : false
                    }

                    Text {
                        text: {
                            if (!dashboardController) return qsTr("غير متاح")
                            return dashboardController.isOnline 
                                ? (dashboardController.isSyncing ? qsTr("مزامنة جارية...") : qsTr("متصل"))
                                : qsTr("غير متصل")
                        }
                        font: Theme.bodyMediumFont
                        color: Theme.onSurfaceVariant
                    }

                    Text {
                        text: "•"
                        color: Theme.onSurfaceVariant
                        visible: dashboardController && dashboardController.currentPenLabel
                    }

                    Text {
                        text: dashboardController ? qsTr("القلم: %1").arg(dashboardController.currentPenLabel) : ""
                        font: Theme.bodyMediumFont
                        color: Theme.onSurfaceVariant
                        visible: dashboardController && dashboardController.currentPenLabel
                    }

                    Text {
                        text: "•"
                        color: Theme.onSurfaceVariant
                        visible: operatorName
                    }

                    Text {
                        text: operatorName ? qsTr("المشغل: %1").arg(operatorName) : ""
                        font: Theme.bodyMediumFont
                        color: Theme.onSurfaceVariant
                        visible: operatorName
                    }
                }
            }

            // Switch User Button
            Button {
                Layout.preferredWidth: 80
                Layout.preferredHeight: 36
                text: qsTr("تبديل")
                icon.source: Theme.legacyIconPath("switch-user.svg")
                
                onClicked: {
                    if (dashboardController) {
                        dashboardController.switchUser()
                    }
                }
            }
        }

        // Quick Stats Section - Fixed height  
        GridLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            columns: 3
            rowSpacing: 8
            columnSpacing: 8

            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("إجمالي الناخبين")
                value: dashboardController ? dashboardController.totalVoters : 0
                subtitle: qsTr("في هذا القلم")
                iconSource: Theme.legacyIconPath("search-voters.svg")
                accentColor: Theme.primary
                isAnimating: dashboardController ? dashboardController.isRefreshing : false
            }

            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("الناخبون المتبقون")
                value: dashboardController ? (dashboardController.totalVoters - dashboardController.totalVotersVoted) : 0
                subtitle: qsTr("لم يصوتوا بعد")
                iconSource: Theme.legacyIconPath("pending-voters.svg")
                accentColor: Theme.warning
                isAnimating: dashboardController ? dashboardController.isRefreshing : false
            }

            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("جلسات الفرز")
                value: dashboardController ? dashboardController.activeSessions : 0
                subtitle: qsTr("نشطة حالياً")
                iconSource: Theme.legacyIconPath("tally-count.svg")
                accentColor: Theme.success
                isAnimating: dashboardController ? dashboardController.isRefreshing : false
            }
        }

        // Main Actions Section - Takes remaining space
        GridLayout {
            id: gridLayout
            Layout.fillWidth: true
            Layout.fillHeight: true  // Takes all remaining vertical space
            columns: 2
            rowSpacing: 16  // Increased spacing for better visual hierarchy
            columnSpacing: 16

            // Voter Search & Check-in (Large)
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 200  // Larger minimum height

                title: qsTr("البحث في الناخبين")
                subtitle: qsTr("البحث وتسجيل الدخول للتصويت")
                iconSource: Theme.legacyIconPath("voter-search.svg")
                badgeVisible: dashboardController ? dashboardController.pendingVoters > 0 : false
                badgeCount: dashboardController ? dashboardController.pendingVoters : 0
                
                // Accessibility
                accessibleName: qsTr("البحث في الناخبين")
                accessibleDescription: qsTr("البحث عن الناخبين وتسجيل دخولهم للتصويت")
                tooltip: qsTr("البحث في الناخبين (Ctrl+F)")

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openVoterSearch()
                    }
                }
            }

            // Tally Counting (Large)
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 200

                title: qsTr("فرز الأصوات")
                subtitle: qsTr("تسجيل وإرسال نتائج الفرز")
                iconSource: Theme.legacyIconPath("ballot-count.svg")
                badgeVisible: dashboardController ? dashboardController.activeSessions > 0 : false
                badgeCount: dashboardController ? dashboardController.activeSessions : 0
                badgeColor: Theme.warning
                
                // Accessibility
                accessibleName: qsTr("فرز الأصوات")
                accessibleDescription: qsTr("تسجيل وإرسال نتائج فرز الأصوات")
                tooltip: qsTr("فرز الأصوات (Ctrl+T)")

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openTallyCounting()
                    }
                }
            }

            // Reports & Statistics
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 150

                title: qsTr("تقارير الإقبال")
                subtitle: qsTr("إحصائيات التصويت")
                iconSource: Theme.legacyIconPath("turnout-stats.svg")

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openTurnoutReports()
                    }
                }
            }

            // Sync Status
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 150

                title: qsTr("حالة المزامنة")
                subtitle: qsTr("إدارة البيانات المتزامنة")
                iconSource: Theme.legacyIconPath("sync-status.svg")
                loading: dashboardController ? dashboardController.isSyncing : false
                badgeVisible: syncStatusController ? syncStatusController.pendingChanges > 0 : false
                badgeCount: syncStatusController ? syncStatusController.pendingChanges : 0
                badgeColor: Theme.warning

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openSyncStatus()
                    }
                }
            }
        }

        // Error Display - Only shows when there's an error
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            radius: 8
            color: Theme.errorContainer
            visible: dashboardController && dashboardController.errorMessage && dashboardController.errorMessage.length > 0

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                SvgIcon {
                    source: Theme.legacyIconPath("error.svg")
                    iconSize: 20
                    color: Theme.onErrorContainer
                }

                Text {
                    Layout.fillWidth: true
                    text: dashboardController ? dashboardController.errorMessage : ""
                    font: Theme.bodyMediumFont
                    color: Theme.onErrorContainer
                    wrapMode: Text.WordWrap
                }

                Button {
                    text: qsTr("إغلاق")
                    flat: true
                    Layout.preferredHeight: 30
                    onClicked: {
                        if (dashboardController) {
                            dashboardController.clearError()
                        }
                    }
                }
            }
        }
    }

    // Connection to dashboard controller for data updates
    Connections {
        target: dashboardController
        function onDataUpdated() {
            // This will trigger property bindings to update
        }
        
        function onPulseRequested() {
            // Trigger pulse animation on all tiles with badges
            for (var i = 0; i < gridLayout.children.length; i++) {
                var tile = gridLayout.children[i]
                if (tile && tile.badgeVisible) {
                    tile.pulse()
                }
            }
        }
    }
} 