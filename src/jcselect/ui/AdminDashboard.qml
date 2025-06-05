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

    color: Theme.background

    // Replace ScrollView with direct ColumnLayout for no scrolling
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16  // Reduced from 24
        spacing: 12  // Reduced from Theme.spacing * 3

        // Enhanced Header Section - Fixed height
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 60  // Fixed height for header
            spacing: 16

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4  // Reduced spacing

                Text {
                    text: qsTr("لوحة إدارة الانتخابات")
                    font: Theme.headlineLargeFont
                    color: Theme.onBackground
                }

                RowLayout {
                    spacing: 8  // Reduced from 12

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
                        visible: dashboardController && dashboardController.lastSyncTime
                    }

                    Text {
                        text: dashboardController ? 
                            qsTr("آخر مزامنة: %1").arg(dashboardController.lastSyncTime.toLocaleString(Qt.locale(), "hh:mm")) 
                            : ""
                        font: Theme.bodyMediumFont
                        color: Theme.onSurfaceVariant
                        visible: dashboardController && dashboardController.lastSyncTime
                    }
                }
            }

            // Refresh Button
            Button {
                Layout.preferredWidth: 80
                Layout.preferredHeight: 36
                text: qsTr("تحديث")
                icon.source: Theme.legacyIconPath("refresh.svg")
                enabled: dashboardController && !dashboardController.isRefreshing
                
                BusyIndicator {
                    anchors.centerIn: parent
                    visible: dashboardController && dashboardController.isRefreshing
                    running: visible
                    width: 20
                    height: 20
                }
                
                onClicked: {
                    if (dashboardController) {
                        dashboardController.refreshDashboardData()
                    }
                }
            }

            // User Menu
            Button {
                id: userMenuButton
                Layout.preferredWidth: 40
                Layout.preferredHeight: 36
                text: "⚙️"
                flat: true
                
                onClicked: userMenu.open()

                Menu {
                    id: userMenu
                    y: parent.height

                    MenuItem {
                        text: qsTr("إدارة المستخدمين")
                        icon.source: Theme.legacyIconPath("user-management.svg")
                        onTriggered: {
                            if (dashboardController) {
                                dashboardController.openUserManagement()
                            }
                        }
                    }

                    MenuItem {
                        text: qsTr("الإعدادات")
                        icon.source: Theme.legacyIconPath("settings.svg")
                        onTriggered: {
                            if (dashboardController) {
                                dashboardController.openSettings()
                            }
                        }
                    }

                    MenuSeparator {}

                    MenuItem {
                        text: qsTr("تبديل المستخدم")
                        icon.source: Theme.legacyIconPath("switch-user.svg")
                        onTriggered: {
                            if (dashboardController) {
                                dashboardController.switchUser()
                            }
                        }
                    }

                    MenuItem {
                        text: qsTr("تسجيل الخروج")
                        icon.source: Theme.legacyIconPath("logout.svg")
                        onTriggered: {
                            if (dashboardController) {
                                dashboardController.logout()
                            }
                        }
                    }
                }
            }
        }

        // Quick Stats Section - Fixed height
        GridLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 80  // Reduced from 100
            columns: 4
            rowSpacing: 8  // Reduced
            columnSpacing: 8  // Reduced

            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("الناخبون المسجلون")
                value: dashboardController ? dashboardController.totalVotersRegistered : 0
                subtitle: qsTr("إجمالي المسجلين")
                iconSource: Theme.legacyIconPath("search-voters.svg")
                accentColor: Theme.primary
                isAnimating: dashboardController ? dashboardController.isRefreshing : false
            }

            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("الأصوات المسجلة")
                value: dashboardController ? dashboardController.totalVotersVoted : 0
                subtitle: qsTr("تم التصويت")
                iconSource: Theme.legacyIconPath("ballot-count.svg")
                accentColor: Theme.success
                isAnimating: dashboardController ? dashboardController.isRefreshing : false
            }

            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("جلسات الفرز النشطة")
                value: dashboardController ? dashboardController.activeTallySessions : 0
                subtitle: qsTr("قيد التنفيذ")
                iconSource: Theme.legacyIconPath("tally-count.svg")
                accentColor: Theme.warning
                isAnimating: dashboardController ? dashboardController.isRefreshing : false
            }

            MetricCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("عمليات المزامنة")
                value: dashboardController ? dashboardController.pendingSyncOperations : 0
                subtitle: qsTr("في الانتظار")
                iconSource: Theme.legacyIconPath("sync-status.svg")
                accentColor: Theme.error
                isAnimating: dashboardController ? dashboardController.isRefreshing : false
            }
        }

        // System Management Section Title - Fixed height
        Text {
            text: qsTr("إدارة النظام")
            font: Theme.titleLargeFont
            color: Theme.onBackground
            Layout.preferredHeight: 30  // Fixed height
        }

        // Main Dashboard Grid - This takes remaining space
        GridLayout {
            id: gridLayout
            Layout.fillWidth: true
            Layout.fillHeight: true  // Takes all remaining vertical space
            columns: root.width >= 1200 ? 3 : 2
            rowSpacing: 12  // Reduced
            columnSpacing: 12  // Reduced

            // Voter Search & Check-in
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                title: qsTr("البحث في الناخبين")
                subtitle: qsTr("البحث وتسجيل الدخول")
                iconSource: Theme.legacyIconPath("voter-search.svg")
                badgeVisible: dashboardController ? dashboardController.pendingVoters > 0 : false
                badgeCount: dashboardController ? dashboardController.pendingVoters : 0
                
                // Accessibility
                accessibleName: qsTr("البحث في الناخبين")
                accessibleDescription: qsTr("البحث عن الناخبين وتسجيل دخولهم للتصويت. اضغط مفتاح الدخول للفتح.")
                tooltip: qsTr("البحث في الناخبين (Ctrl+F)")

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openVoterSearch()
                    }
                }
            }

            // Vote Counting
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                title: qsTr("فرز الأصوات")
                subtitle: qsTr("تسجيل نتائج الفرز")
                iconSource: Theme.legacyIconPath("ballot-count.svg")
                badgeVisible: dashboardController ? dashboardController.activeSessions > 0 : false
                badgeCount: dashboardController ? dashboardController.activeSessions : 0
                badgeColor: Theme.warning
                
                // Accessibility
                accessibleName: qsTr("فرز الأصوات")
                accessibleDescription: qsTr("إدخال وتسجيل نتائج فرز الأصوات. اضغط مفتاح الدخول للفتح.")
                tooltip: qsTr("فرز الأصوات (Ctrl+T)")

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openTallyCounting()
                    }
                }
            }

            // Live Results
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                title: qsTr("النتائج المباشرة")
                subtitle: qsTr("متابعة تقدم العد")
                iconSource: Theme.legacyIconPath("live-results.svg")
                badgeVisible: dashboardController ? dashboardController.hasNewResults : false
                badgeCount: 1
                badgeColor: Theme.success
                
                // Accessibility
                accessibleName: qsTr("النتائج المباشرة")
                accessibleDescription: qsTr("عرض النتائج المباشرة للانتخابات ومتابعة تقدم العد. اضغط مفتاح الدخول للفتح.")
                tooltip: qsTr("النتائج المباشرة (Ctrl+R)")

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openLiveResults()
                    }
                }
            }

            // Sync Status
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                title: qsTr("حالة المزامنة")
                subtitle: qsTr("إدارة البيانات المتزامنة")
                iconSource: Theme.legacyIconPath("sync-status.svg")
                loading: dashboardController ? dashboardController.isSyncing : false

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openSyncStatus()
                    }
                }
            }

            // Audit Logs
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                title: qsTr("سجلات التدقيق")
                subtitle: qsTr("مراجعة العمليات")
                iconSource: Theme.legacyIconPath("audit-logs.svg")
                badgeVisible: dashboardController ? dashboardController.hasUnreadAuditLogs : false
                badgeCount: 3

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openAuditLogs()
                    }
                }
            }

            // System Settings
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                title: qsTr("إعدادات النظام")
                subtitle: qsTr("تكوين الإعدادات")
                iconSource: Theme.legacyIconPath("system-settings.svg")

                onClicked: {
                    if (dashboardController) {
                        dashboardController.openSystemSettings()
                    }
                }
            }
        }

        // Error Display - Only shows when there's an error
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 50  // Fixed compact height
            radius: 8
            color: Theme.errorContainer
            visible: dashboardController && dashboardController.errorMessage.length > 0

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12  // Reduced margins
                spacing: 8  // Reduced spacing

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
                    Layout.preferredHeight: 30  // Smaller button
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