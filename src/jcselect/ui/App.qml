import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect 1.0
import jcselect.ui 1.0
import jcselect.components 1.0

ApplicationWindow {
    id: root
    
    width: 1200
    height: 800
    visible: true
    title: qsTr("jcselect - Voter Tracking System")
    
    // Enable RTL mirroring for Arabic
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true
    
    // Application state management
    QtObject {
        id: appState
        
        // Application modes
        property string currentMode: "login"  // login, admin_dashboard, operator_dashboard, voter_search, reports, settings
        property bool isInitialized: false
        property bool hasActiveSession: false
        property bool isLoggedIn: false
        
        // Current user session
        property var currentUser: null
        property string currentOperatorId: ""
        property string currentOperatorName: ""
        property string selectedPen: ""
        
        // UI state
        property bool isOnline: syncStatus.isOnline
        property int totalVotersToday: 0
        property int votedCount: 0
        
        // State change signals
        signal modeChanged(string newMode)
        signal sessionChanged(bool hasSession)
        signal statsUpdated(int total, int voted)
        signal userLoggedIn(var user)
        signal userLoggedOut()
        
        // State management functions
        function switchMode(newMode) {
            if (currentMode !== newMode) {
                var oldMode = currentMode;
                currentMode = newMode;
                console.log("Mode changed from", oldMode, "to", newMode);
                modeChanged(newMode);
            }
        }
        
        function updateVoterStats(total, voted) {
            totalVotersToday = total;
            votedCount = voted;
            statsUpdated(total, voted);
        }
        
        function loginUser(user, penId) {
            currentUser = user;
            currentOperatorId = user.user_id || "";
            currentOperatorName = user.full_name || user.username || "";
            selectedPen = penId || "";
            isLoggedIn = true;
            hasActiveSession = true;
            
            // Set pen label in dashboard controller
            if (dashboardController && penId) {
                dashboardController.setPenLabel(penId);
            }
            
            // Determine which dashboard to show based on user role
            if (user.role === "admin") {
                switchMode("admin_dashboard");
            } else {
                switchMode("operator_dashboard");
            }
            
            userLoggedIn(user);
        }
        
        function logoutUser() {
            currentUser = null;
            currentOperatorId = "";
            currentOperatorName = "";
            selectedPen = "";
            isLoggedIn = false;
            hasActiveSession = false;
            switchMode("login");
            userLoggedOut();
        }
        
        function initializeApp() {
            isInitialized = true;
            // Try auto-login if possible
            if (loginController) {
                var autoLoginSuccess = loginController.autoLoginIfPossible();
                if (!autoLoginSuccess) {
                    switchMode("login");
                }
            } else {
                switchMode("login");
            }
        }
        
        Component.onCompleted: {
            initializeApp();
        }
    }
    
    // Sync engine reference (use global context property from main.py)
    property var syncEngine: syncStatus || null
    
    // Application controller
    AppController {
        id: appController
    }
    
    // Voter search controller
    VoterSearchController {
        id: voterController
    }
    
    // Connection to login controller
    Connections {
        target: loginController
        
        function onLoginSuccessful(userInfo) {
            console.log("=== onLoginSuccessful signal received ===");
            console.log("User info:", JSON.stringify(userInfo));
            console.log("Login successful for user:", userInfo.username);
            appState.loginUser(userInfo, loginController ? loginController.selectedPen : "");
        }
        
        function onLoginFailed(errorMessage) {
            console.log("=== onLoginFailed signal received ===");
            console.log("Login failed:", errorMessage);
            // Show error message (could add a snackbar here)
        }
        
        function onPenSelectionRequired() {
            console.log("=== onPenSelectionRequired signal received ===");
            console.log("Pen selection required");
            penPickerDialog.open();
        }
        
        function onPenSelectionCompleted(penId) {
            console.log("=== onPenSelectionCompleted signal received ===");
            console.log("Pen selected:", penId);
            penPickerDialog.close();
        }
        
        function onLogoutCompleted() {
            console.log("=== onLogoutCompleted signal received ===");
            console.log("Logout completed");
            appState.logoutUser();
        }
    }
    
    // Connection to dashboard controller
    Connections {
        target: dashboardController
        
        function onNavigationRequested(screenName) {
            console.log("Navigation requested to:", screenName);
            // Handle navigation to different screens
            appState.switchMode(screenName);
        }
        
        function onUserSwitchRequested() {
            console.log("User switch requested");
            if (loginController) {
                loginController.logout();
            }
        }
    }
    
    // Sync status connections
    Connections {
        target: syncStatus
        
        function onSyncCompleted(changesCount) {
            if (changesCount > 0) {
                syncSnackbar.show(
                    qsTr("تم مزامنة %1 تغيير").arg(changesCount),
                    Snackbar.Success
                );
            }
        }
        
        function onSyncFailed(errorMessage) {
            syncSnackbar.show(
                qsTr("فشل في المزامنة: %1").arg(errorMessage),
                Snackbar.Error
            );
        }
        
        function onSyncStarted() {
            console.log("Sync started");
        }
    }
    
    // Global keyboard shortcuts
    Shortcut {
        sequence: "Ctrl+F"
        enabled: appState.currentMode === "voter_search"
        onActivated: {
            if (voterSearchWindow) {
                voterSearchWindow.searchBar.forceActiveFocus();
            }
        }
    }
    
    Shortcut {
        sequence: "Ctrl+R"
        enabled: appState.currentMode === "voter_search"
        onActivated: {
            voterController.refreshSearch();
        }
    }
    
    Shortcut {
        sequence: "Escape"
        enabled: appState.currentMode === "voter_search"
        onActivated: {
            voterController.clearSelection();
        }
    }
    
    // Sync shortcut
    Shortcut {
        sequence: "Ctrl+S"
        onActivated: {
            syncStatus.forcSync();
        }
    }
    
    // Dashboard shortcuts
    Shortcut {
        sequence: "Ctrl+F"
        enabled: appState.currentMode === "admin_dashboard" || appState.currentMode === "operator_dashboard"
        onActivated: {
            if (dashboardController) {
                dashboardController.openVoterSearch()
            }
        }
    }
    
    Shortcut {
        sequence: "Ctrl+T"
        enabled: appState.currentMode === "admin_dashboard" || appState.currentMode === "operator_dashboard"
        onActivated: {
            if (dashboardController) {
                dashboardController.openTallyCounting()
            }
        }
    }
    
    Shortcut {
        sequence: "Ctrl+R"
        enabled: appState.currentMode === "admin_dashboard"
        onActivated: {
            if (dashboardController) {
                dashboardController.openLiveResults()
            }
        }
    }
    
    Shortcut {
        sequence: "Ctrl+D"
        enabled: appState.currentMode !== "login"
        onActivated: {
            // Return to dashboard
            var targetMode = appState.currentUser && appState.currentUser.role === "admin" ? "admin_dashboard" : "operator_dashboard"
            appState.switchMode(targetMode)
        }
    }
    
    // Main content area
    Rectangle {
        anchors.fill: parent
        color: Theme.surfaceColor
        
        // Main application content based on current mode
        Loader {
            id: mainContentLoader
            anchors.fill: parent
            
            sourceComponent: {
                switch (appState.currentMode) {
                    case "login":
                        return loginComponent;
                    case "admin_dashboard":
                        return adminDashboardComponent;
                    case "operator_dashboard":
                        return operatorDashboardComponent;
                    case "voter_search":
                        return voterSearchComponent;
                    case "tally_counting":
                        return tallyCountingComponent;
                    case "live_results":
                        if (appState.currentUser && appState.currentUser.role === "admin") {
                            return resultsWindowComponent;
                        }
                        return adminDashboardComponent; // Fallback to dashboard
                    case "turnout_reports":
                        return turnoutReportsComponent;
                    case "results_charts":
                        return resultsChartsComponent;
                    case "winners":
                        return winnersComponent;
                    case "count_operations":
                        return countOperationsComponent;
                    case "setup":
                        return setupComponent;
                    case "system_settings":
                        return systemSettingsComponent;
                    case "reports":
                        return reportsComponent;
                    case "settings":
                        return settingsComponent;
                    default:
                        return loginComponent;
                }
            }
        }
    }
    
    // Login component
    Component {
        id: loginComponent
        
        LoginWindow {
            // The LoginWindow will access the global loginController context property directly
            // No need to pass it as a property since it's already available globally
        }
    }
    
    // Admin dashboard component
    Component {
        id: adminDashboardComponent
        
        AdminDashboard {
            dashboardController: dashboardController
        }
    }
    
    // Operator dashboard component
    Component {
        id: operatorDashboardComponent
        
        OperatorDashboard {
            dashboardController: dashboardController
            syncStatusController: syncStatus
            syncEngine: root.syncEngine
            operatorName: appState.currentOperatorName
        }
    }
    
    // Components for different application modes
    Component {
        id: voterSearchComponent
        
        VoterSearchWindow {
            id: voterSearchWindow
            controller: voterController
            
            // Connect voter marking to app state
            Connections {
                target: voterController
                function onVoterMarkedSuccessfully(voterName) {
                    // Update stats when voter is marked
                    appState.updateVoterStats(
                        appState.totalVotersToday,
                        appState.votedCount + 1
                    );
                }
            }
        }
    }
    
    Component {
        id: reportsComponent
        
        Rectangle {
            color: Theme.surfaceColor
            
            Label {
                anchors.centerIn: parent
                text: qsTr("Reports Module - Coming Soon")
                font.pixelSize: Theme.titleSize
                color: Theme.textColor
            }
        }
    }
    
    Component {
        id: settingsComponent
        
        Rectangle {
            color: Theme.surfaceColor
            
            Label {
                anchors.centerIn: parent
                text: qsTr("Settings Module - Coming Soon")
                font.pixelSize: Theme.titleSize
                color: Theme.textColor
            }
        }
    }
    
    // Results window component
    Component {
        id: resultsWindowComponent
        
        ResultsWindow {
            id: resultsWindow
            
            // TODO: Pass actual ResultsController instance
            // resultsController: resultsControllerInstance
        }
    }
    
    // TODO: Navigation screen components
    Component {
        id: tallyCountingComponent
        
        TallyCountingWindow {
            id: tallyCountingWindow
            
            // Initialize the tally session when the component loads
            Component.onCompleted: {
                if (appState.currentOperatorId && appState.selectedPen) {
                    tallyController.initializeSession(
                        appState.selectedPen,
                        appState.currentOperatorId,
                        "Pen " + appState.selectedPen
                    );
                }
            }
            
            // Connect tally events to app state
            Connections {
                target: tallyCountingWindow.tallyController
                
                function onBallotConfirmed(ballotNumber) {
                    console.log("Ballot confirmed in app:", ballotNumber);
                    // Could update app-wide statistics here
                }
                
                function onRecountCompleted() {
                    console.log("Recount completed in app");
                }
                
                function onErrorOccurred(errorMessage) {
                    console.error("Tally error in app:", errorMessage);
                    // Could show app-wide error notification
                }
            }
        }
    }
    
    Component {
        id: turnoutReportsComponent
        
        Rectangle {
            color: Theme.surfaceColor
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: Theme.spacing
                
                Text {
                    text: "📈"
                    font.pixelSize: 48
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("Turnout Reports Module")
                    font.pixelSize: Theme.titleSize
                    font.weight: Font.Bold
                    color: Theme.textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("TODO: Implement turnout statistics interface")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.7
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Button {
                    text: qsTr("Back to Dashboard")
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: appState.switchMode("admin_dashboard")
                }
            }
        }
    }
    
    Component {
        id: resultsChartsComponent
        
        Rectangle {
            color: Theme.surfaceColor
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: Theme.spacing
                
                Text {
                    text: "📊"
                    font.pixelSize: 48
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("Results Charts Module")
                    font.pixelSize: Theme.titleSize
                    font.weight: Font.Bold
                    color: Theme.textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("TODO: Implement Bershaan & Flaan analysis charts")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.7
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Button {
                    text: qsTr("Back to Dashboard")
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: appState.switchMode("admin_dashboard")
                }
            }
        }
    }
    
    Component {
        id: winnersComponent
        
        Rectangle {
            color: Theme.surfaceColor
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: Theme.spacing
                
                Text {
                    text: "🏆"
                    font.pixelSize: 48
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("Winners Module")
                    font.pixelSize: Theme.titleSize
                    font.weight: Font.Bold
                    color: Theme.textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("TODO: Implement elected candidates interface")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.7
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Button {
                    text: qsTr("Back to Dashboard")
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: appState.switchMode("admin_dashboard")
                }
            }
        }
    }
    
    Component {
        id: countOperationsComponent
        
        Rectangle {
            color: Theme.surfaceColor
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: Theme.spacing
                
                Text {
                    text: "⚙️"
                    font.pixelSize: 48
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("Count Operations Module")
                    font.pixelSize: Theme.titleSize
                    font.weight: Font.Bold
                    color: Theme.textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("TODO: Implement counting process management")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.7
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Button {
                    text: qsTr("Back to Dashboard")
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: appState.switchMode("admin_dashboard")
                }
            }
        }
    }
    
    Component {
        id: setupComponent
        
        Rectangle {
            color: Theme.surfaceColor
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: Theme.spacing
                
                Text {
                    text: "🔧"
                    font.pixelSize: 48
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("Setup Module")
                    font.pixelSize: Theme.titleSize
                    font.weight: Font.Bold
                    color: Theme.textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("TODO: Implement parties, pens & teams management")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.7
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Button {
                    text: qsTr("Back to Dashboard")
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: appState.switchMode("admin_dashboard")
                }
            }
        }
    }
    
    Component {
        id: systemSettingsComponent
        
        Rectangle {
            color: Theme.surfaceColor
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: Theme.spacing
                
                Text {
                    text: "⚙️"
                    font.pixelSize: 48
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("System Settings Module")
                    font.pixelSize: Theme.titleSize
                    font.weight: Font.Bold
                    color: Theme.textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Label {
                    text: qsTr("TODO: Implement app configuration interface")
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.7
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Button {
                    text: qsTr("Back to Dashboard")
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: appState.switchMode("admin_dashboard")
                }
            }
        }
    }
    
    // Pen picker dialog
    PenPickerDialog {
        id: penPickerDialog
        
        onAccepted: {
            console.log("Pen picker accepted");
        }
        
        onRejected: {
            console.log("Pen picker rejected");
        }
    }
    
    // Status bar or overlay for displaying app state info
    Rectangle {
        id: statusBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 24
        color: Theme.elevation1
        visible: appState.isInitialized && appState.isLoggedIn
        
        RowLayout {
            anchors.left: parent.left
            anchors.leftMargin: Theme.spacingMedium
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.spacingMedium
            
            Label {
                text: qsTr("المشغل: %1").arg(appState.currentOperatorName)
                font.pixelSize: Theme.captionSize
                color: Theme.textColor
            }
            
            Rectangle {
                width: 1
                height: 16
                color: Theme.textColor
                opacity: 0.3
            }
            
            // Sync status indicator
            RowLayout {
                spacing: Theme.spacingTiny
                
                Text {
                    text: syncStatus.isOnline ? "📡" : "📴"
                    font.pixelSize: 12
                }
                
                Label {
                    text: syncStatus.isOnline ? qsTr("متصل") : qsTr("غير متصل")
                    font.pixelSize: Theme.captionSize
                    color: syncStatus.isOnline ? Theme.successColor : Theme.errorColor
                }
                
                // Show pending count if any
                Label {
                    visible: syncStatus.pendingChanges > 0
                    text: qsTr("(%1 معلق)").arg(syncStatus.pendingChanges)
                    font.pixelSize: Theme.captionSize
                    color: Theme.warningColor
                }
                
                // Sync progress indicator
                Rectangle {
                    width: 40
                    height: 4
                    radius: 2
                    color: Theme.elevation2
                    visible: syncStatus.syncProgress > 0 && syncStatus.syncProgress < 1
                    
                    Rectangle {
                        width: parent.width * syncStatus.syncProgress
                        height: parent.height
                        radius: parent.radius
                        color: Theme.primaryColor
                    }
                }
                
                // Click to get tooltip
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    
                    ToolTip.visible: containsMouse
                    ToolTip.text: {
                        let tooltip = qsTr("حالة المزامنة: %1").arg(syncStatus.getStatusText());
                        if (syncStatus.lastSyncTime.toString() !== "") {
                            tooltip += qsTr("\nآخر مزامنة: %1").arg(syncStatus.getLastSyncTimeFormatted());
                        }
                        if (syncStatus.syncEnabled) {
                            tooltip += qsTr("\nمزامنة تلقائية كل %1 ثانية").arg(syncStatus.syncInterval);
                        } else {
                            tooltip += qsTr("\nالمزامنة معطلة");
                        }
                        return tooltip;
                    }
                    
                    onClicked: {
                        syncStatus.refreshStatus();
                    }
                }
            }
            
            Rectangle {
                width: 1
                height: 16
                color: Theme.textColor
                opacity: 0.3
            }
            
            Label {
                text: qsTr("صوت اليوم: %1/%2").arg(appState.votedCount).arg(appState.totalVotersToday)
                font.pixelSize: Theme.captionSize
                color: Theme.textColor
            }
        }
    }
    
    // Sync notification snackbar
    Snackbar {
        id: syncSnackbar
        anchors.bottom: statusBar.visible ? statusBar.top : parent.bottom
        anchors.bottomMargin: Theme.spacingMedium
    }
} 