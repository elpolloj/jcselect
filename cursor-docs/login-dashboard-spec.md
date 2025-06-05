
# JCSELECT Login & Dashboard System - Technical Specification

## 1. Overview

Implement a comprehensive authentication and dashboard system for jcselect that supports both admin and operator roles with separate entry points. The system provides offline-first login with token caching, pen selection, and role-based Material 3 dashboards that serve as the main navigation interface for the application.

## 2. Technical Requirements

### 2.1 Authentication Architecture
- **Online Authentication**: JWT-based login via `/auth/login` endpoint
- **Offline Fallback**: Cached credential validation when server unavailable
- **Token Management**: Automatic refresh with 15-minute access tokens and 12-hour refresh tokens
- **Session Persistence**: Secure credential storage in `~/.jcselect/credentials.json`
- **Role Validation**: Server-side role verification with client-side enforcement

### 2.2 Application Entry Points
- **Admin Mode**: `python -m JCSELECT.admin` → Full admin dashboard
- **Operator Mode**: `python -m JCSELECT.operator` → Limited operator dashboard
- **Single Codebase**: Role-based UI gating with shared components
- **Build Variants**: Different desktop shortcuts but same executable

### 2.3 Dashboard Design System
- **Framework**: Material 3 design language with Arabic RTL support
- **Layout**: Responsive grid system (3 columns for admin, 2 for operator)
- **Components**: Reusable card tiles with icons, badges, and hover effects
- **Navigation**: Keyboard accessibility with focus management
- **Theming**: Consistent with existing Theme.qml system

### 2.4 Session Management
- **Persistence**: Automatic session restoration on app restart
- **Security**: Encrypted token storage with expiry validation
- **Pen Selection**: Persistent pen assignment with modal picker
- **Background Refresh**: Silent token renewal without UI interruption
- **Logout**: Secure credential cleanup with app restart

## 3. Architecture Design

### 3.1 Authentication Flow
```
App Launch → Check Cached Token → Valid? → Dashboard
     ↓              ↓              ↓         ↓
Entry Point    Auth Cache     Auto-Login   Role Check
     ↓              ↓              ↓         ↓
Login Dialog   Token Refresh   Pen Picker  Show Dashboard
```

### 3.2 Component Architecture
```
App.qml
├── LoginWindow.qml
│   ├── LoginForm.qml
│   └── PenPickerDialog.qml
├── AdminDashboard.qml
│   ├── DashboardGrid.qml
│   └── CardTile.qml (8 tiles)
├── OperatorDashboard.qml
│   ├── DashboardGrid.qml
│   └── CardTile.qml (2 tiles)
└── Shared/
    ├── IconButton.qml
    ├── UserMenuButton.qml
    └── StatusIndicator.qml
```

### 3.3 Controller Pattern
```
LoginController
├── authenticate(username, password)
├── autoLoginIfPossible()
├── refreshTokenLoop()
└── logout()

DashboardRouter
├── determineUserRole()
├── showDashboard()
└── handleNavigation()

PenPickerController
├── getAvailablePens()
├── selectPen(penId)
└── persistPenSelection()
```

## 4. Detailed Implementation Plan

### Step 1: Authentication Cache System

**File**: `src/JCSELECT/utils/auth_cache.py`

**Credential Storage Schema**:
```python
class CachedCredentials(BaseModel):
    """Secure credential cache model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    refresh_expires_at: datetime
    user_info: UserInfo
    selected_pen_id: Optional[str] = None
    last_login: datetime
    
class AuthCache:
    """Manages persistent authentication cache"""
    
    def __init__(self):
        self.cache_path = Path.home() / ".jcselect" / "credentials.json"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    def save_credentials(self, credentials: CachedCredentials) -> None:
        """Save encrypted credentials to cache file"""
        # Encrypt sensitive fields before storage
        encrypted_data = self._encrypt_credentials(credentials)
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(encrypted_data, f, indent=2, default=str)
    
    def load_credentials(self) -> Optional[CachedCredentials]:
        """Load and decrypt cached credentials"""
        if not self.cache_path.exists():
            return None
        
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                encrypted_data = json.load(f)
            
            return self._decrypt_credentials(encrypted_data)
        except Exception as e:
            logger.warning(f"Failed to load cached credentials: {e}")
            return None
    
    def clear_credentials(self) -> None:
        """Securely clear cached credentials"""
        if self.cache_path.exists():
            self.cache_path.unlink()
    
    def is_token_valid(self, credentials: CachedCredentials) -> bool:
        """Check if access token is still valid"""
        return datetime.utcnow() < credentials.expires_at
    
    def can_refresh_token(self, credentials: CachedCredentials) -> bool:
        """Check if refresh token is still valid"""
        return datetime.utcnow() < credentials.refresh_expires_at
```

**Encryption Utilities**:
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class TokenEncryption:
    """Handle token encryption/decryption"""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.fernet = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key based on machine ID"""
        key_file = Path.home() / ".jcselect" / ".key"
        
        if key_file.exists():
            return key_file.read_bytes()
        
        # Generate key from machine-specific data
        machine_id = self._get_machine_id()
        salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        
        # Store key securely
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Owner read/write only
        
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
```

### Step 2: Login Controller Implementation

**File**: `src/JCSELECT/controllers/login_controller.py`

```python
class LoginController(QObject):
    """Handles authentication, token management, and session persistence"""
    
    # Signals
    loginSuccessful = Signal(dict)  # user_info
    loginFailed = Signal(str)  # error_message
    tokenRefreshed = Signal()
    logoutCompleted = Signal()
    penSelectionRequired = Signal()
    penSelectionCompleted = Signal(str)  # pen_id
    
    # Properties
    isLoggedIn = Property(bool, notify=loginSuccessful)
    currentUser = Property('QVariant', notify=loginSuccessful)
    isOnline = Property(bool, notify=connectionStatusChanged)
    selectedPen = Property('QVariant', notify=penSelectionCompleted)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_cache = AuthCache()
        self.api_client = APIClient()
        self.jwt_manager = JWTManager()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_token_background)
        self._current_user = None
        self._selected_pen = None
        self._is_online = False
    
    @Slot(str, str, bool)
    def authenticate(self, username: str, password: str, remember_me: bool = True):
        """Authenticate user with online/offline fallback"""
        try:
            # Try online authentication first
            if self._attempt_online_login(username, password, remember_me):
                return
            
            # Fallback to offline authentication
            if self._attempt_offline_login(username, password):
                return
            
            self.loginFailed.emit("Invalid credentials")
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.loginFailed.emit(f"Authentication error: {str(e)}")
    
    def _attempt_online_login(self, username: str, password: str, remember_me: bool) -> bool:
        """Attempt online authentication via API"""
        try:
            response = self.api_client.post("/auth/login", {
                "username": username,
                "password": password
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self._handle_successful_login(token_data, remember_me)
                self._is_online = True
                return True
                
        except Exception as e:
            logger.warning(f"Online login failed: {e}")
            self._is_online = False
        
        return False
    
    def _attempt_offline_login(self, username: str, password: str) -> bool:
        """Attempt offline login with cached credentials"""
        cached_creds = self.auth_cache.load_credentials()
        
        if not cached_creds:
            return False
        
        # Verify username matches cached user
        if cached_creds.user_info.username != username:
            return False
        
        # For offline mode, we rely on the cached token being valid
        # In production, you might want to cache password hash for verification
        if self.auth_cache.can_refresh_token(cached_creds):
            self._handle_cached_login(cached_creds)
            return True
        
        return False
    
    def _handle_successful_login(self, token_data: dict, remember_me: bool):
        """Process successful login response"""
        user_info = token_data["user_info"]
        
        # Calculate expiry times
        expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        refresh_expires_at = datetime.utcnow() + timedelta(hours=12)
        
        # Create cached credentials
        credentials = CachedCredentials(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            user_info=UserInfo(**user_info),
            last_login=datetime.utcnow()
        )
        
        if remember_me:
            self.auth_cache.save_credentials(credentials)
        
        self._current_user = credentials.user_info
        self._start_token_refresh_timer(credentials)
        
        # Check if pen selection is needed
        if not credentials.selected_pen_id:
            self.penSelectionRequired.emit()
        else:
            self._selected_pen = credentials.selected_pen_id
            self.loginSuccessful.emit(user_info)
    
    @Slot()
    def autoLoginIfPossible(self) -> bool:
        """Attempt automatic login with cached credentials"""
        cached_creds = self.auth_cache.load_credentials()
        
        if not cached_creds:
            return False
        
        # Check if we can refresh the token
        if self.auth_cache.can_refresh_token(cached_creds):
            if self.auth_cache.is_token_valid(cached_creds):
                # Token still valid, use directly
                self._handle_cached_login(cached_creds)
                return True
            else:
                # Try to refresh token
                if self._refresh_access_token(cached_creds):
                    return True
        
        # Clear invalid credentials
        self.auth_cache.clear_credentials()
        return False
    
    def _refresh_access_token(self, credentials: CachedCredentials) -> bool:
        """Refresh access token using refresh token"""
        try:
            response = self.api_client.post("/auth/refresh", {
                "refresh_token": credentials.refresh_token
            })
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Update credentials with new access token
                credentials.access_token = token_data["access_token"]
                credentials.expires_at = datetime.utcnow() + timedelta(
                    seconds=token_data["expires_in"]
                )
                
                self.auth_cache.save_credentials(credentials)
                self._handle_cached_login(credentials)
                return True
                
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
        
        return False
    
    @Slot(str)
    def selectPen(self, pen_id: str):
        """Select and persist pen choice"""
        cached_creds = self.auth_cache.load_credentials()
        if cached_creds:
            cached_creds.selected_pen_id = pen_id
            self.auth_cache.save_credentials(cached_creds)
        
        self._selected_pen = pen_id
        self.penSelectionCompleted.emit(pen_id)
        
        # Now emit login successful
        if self._current_user:
            user_dict = self._current_user.__dict__
            self.loginSuccessful.emit(user_dict)
    
    @Slot()
    def logout(self):
        """Logout user and clear all cached data"""
        self.refresh_timer.stop()
        self.auth_cache.clear_credentials()
        self._current_user = None
        self._selected_pen = None
        self.logoutCompleted.emit()
```

### Step 3: Pen Picker Component

**File**: `src/JCSELECT/ui/components/PenPickerDialog.qml`

```qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import JCSELECT 1.0

Dialog {
    id: root
    
    property alias controller: penController
    
    title: qsTr("Select Polling Station")
    modal: true
    closePolicy: Dialog.NoAutoClose
    
    width: 400
    height: 300
    
    anchors.centerIn: parent
    
    PenPickerController {
        id: penController
        
        onPensLoaded: {
            penComboBox.model = availablePens
        }
        
        onSelectionCompleted: {
            root.accept()
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.margin
        spacing: Theme.spacing
        
        Text {
            text: qsTr("Please select your assigned polling station:")
            font.pixelSize: Theme.bodySize
            color: Theme.textColor
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        
        ComboBox {
            id: penComboBox
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.searchBarHeight
            
            textRole: "label"
            valueRole: "id"
            
            delegate: ItemDelegate {
                width: penComboBox.width
                contentItem: ColumnLayout {
                    Text {
                        text: model.label
                        font.pixelSize: Theme.bodySize
                        font.weight: Font.Medium
                        color: Theme.textColor
                    }
                    Text {
                        text: model.town_name
                        font.pixelSize: Theme.captionSize
                        color: Theme.textColor
                        opacity: 0.7
                    }
                }
            }
            
            background: Rectangle {
                color: Theme.surfaceColor
                border.color: Theme.primaryColor
                border.width: penComboBox.activeFocus ? 2 : 1
                radius: Theme.radius
            }
        }
        
        Item { Layout.fillHeight: true }
        
        RowLayout {
            Layout.fillWidth: true
            
            Item { Layout.fillWidth: true }
            
            Button {
                text: qsTr("Confirm Selection")
                enabled: penComboBox.currentIndex >= 0
                
                background: Rectangle {
                    color: parent.enabled ? Theme.primaryColor : Theme.surfaceColor
                    radius: Theme.radius
                }
                
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: Theme.bodySize
                    color: parent.enabled ? "white" : Theme.textColor
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                
                onClicked: {
                    if (penComboBox.currentIndex >= 0) {
                        const selectedPen = penComboBox.model[penComboBox.currentIndex]
                        penController.selectPen(selectedPen.id)
                    }
                }
            }
        }
    }
    
    Component.onCompleted: {
        penController.loadAvailablePens()
    }
}
```

**File**: `src/JCSELECT/controllers/pen_picker_controller.py`

```python
class PenPickerController(QObject):
    """Controller for pen selection dialog"""
    
    # Signals
    pensLoaded = Signal()
    selectionCompleted = Signal(str)  # pen_id
    errorOccurred = Signal(str)  # error_message
    
    # Properties
    availablePens = Property('QVariantList', notify=pensLoaded)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._available_pens = []
    
    @Slot()
    def loadAvailablePens(self):
        """Load available pens from database"""
        try:
            with get_session() as session:
                # Get all active (non-deleted) pens
                pens = session.exec(
                    select(Pen).where(Pen.deleted_at.is_(None))
                ).all()
                
                pen_list = []
                for pen in pens:
                    pen_dict = {
                        "id": str(pen.id),
                        "label": pen.label,
                        "town_name": pen.town_name
                    }
                    pen_list.append(pen_dict)
                
                self._available_pens = pen_list
                self.pensLoaded.emit()
                
        except Exception as e:
            logger.error(f"Failed to load pens: {e}")
            self.errorOccurred.emit(f"Failed to load polling stations: {str(e)}")
    
    @Slot(str)
    def selectPen(self, pen_id: str):
        """Select a pen and emit completion signal"""
        try:
            # Validate pen exists
            with get_session() as session:
                pen = session.get(Pen, pen_id)
                if not pen or pen.deleted_at is not None:
                    self.errorOccurred.emit("Selected polling station is not valid")
                    return
            
            self.selectionCompleted.emit(pen_id)
            logger.info(f"Pen selected: {pen_id}")
            
        except Exception as e:
            logger.error(f"Pen selection failed: {e}")
            self.errorOccurred.emit(f"Selection failed: {str(e)}")
```

### Step 4: Dashboard Components

**File**: `src/JCSELECT/ui/components/CardTile.qml`

```qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Effects

Rectangle {
    id: root
    
    property string title: ""
    property string subtitle: ""
    property string iconSource: ""
    property string badgeText: ""
    property bool badgeVisible: false
    property color badgeColor: Theme.errorColor
    property bool enabled: true
    
    signal clicked()
    signal rightClicked()
    
    width: 200
    height: 160
    
    color: Theme.backgroundColor
    radius: Theme.radius * 2
    
    // Material 3 elevation
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: "#1A000000"
        shadowBlur: hovered ? 0.4 : 0.2
        shadowVerticalOffset: hovered ? 6 : 3
        shadowHorizontalOffset: 0
    }
    
    // Hover state
    property bool hovered: mouseArea.containsMouse
    
    Behavior on scale {
        NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
    }
    
    scale: hovered ? 1.02 : 1.0
    
    // Ripple effect
    Rectangle {
        id: ripple
        anchors.centerIn: parent
        width: 0
        height: 0
        radius: width / 2
        color: Theme.primaryColor
        opacity: 0
        
        PropertyAnimation {
            id: rippleAnimation
            target: ripple
            properties: "width,height,opacity"
            from: 0
            to: root.width * 2
            duration: 300
            easing.type: Easing.OutCubic
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.margin
        spacing: Theme.spacing
        
        // Icon with badge
        Item {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 48
            Layout.preferredHeight: 48
            
            Image {
                anchors.centerIn: parent
                source: root.iconSource
                width: 32
                height: 32
                fillMode: Image.PreserveAspectFit
                
                ColorOverlay {
                    anchors.fill: parent
                    source: parent
                    color: root.enabled ? Theme.primaryColor : Theme.textColor
                    opacity: root.enabled ? 1.0 : 0.5
                }
            }
            
            // Badge
            Rectangle {
                visible: root.badgeVisible && root.badgeText !== ""
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: -4
                anchors.rightMargin: -4
                
                width: Math.max(16, badgeLabel.width + 8)
                height: 16
                radius: 8
                color: root.badgeColor
                
                Text {
                    id: badgeLabel
                    anchors.centerIn: parent
                    text: root.badgeText
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    color: "white"
                }
            }
        }
        
        // Title
        Text {
            Layout.fillWidth: true
            text: root.title
            font.pixelSize: Theme.titleSize
            font.weight: Font.Medium
            color: root.enabled ? Theme.textColor : Theme.textColor
            opacity: root.enabled ? 1.0 : 0.5
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
        
        // Subtitle
        Text {
            Layout.fillWidth: true
            text: root.subtitle
            font.pixelSize: Theme.captionSize
            color: Theme.textColor
            opacity: 0.7
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
            visible: text !== ""
        }
        
        Item { Layout.fillHeight: true }
    }
    
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        
        onClicked: {
            if (!root.enabled) return
            
            if (mouse.button === Qt.LeftButton) {
                rippleAnimation.start()
                root.clicked()
            } else if (mouse.button === Qt.RightButton) {
                root.rightClicked()
            }
        }
    }
    
    // Keyboard focus support
    Keys.onReturnPressed: {
        if (root.enabled) {
            root.clicked()
        }
    }
    
    Keys.onSpacePressed: {
        if (root.enabled) {
            root.clicked()
        }
    }
}
```

### Step 5: Dashboard Layouts

**File**: `src/JCSELECT/ui/AdminDashboard.qml`

```qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import JCSELECT 1.0

Rectangle {
    id: root
    
    property alias controller: dashboardController
    
    color: Theme.backgroundColor
    
    DashboardController {
        id: dashboardController
    }
    
    ScrollView {
        anchors.fill: parent
        anchors.margins: Theme.margin
        
        ColumnLayout {
            width: parent.width
            spacing: Theme.margin
            
            // Header
            RowLayout {
                Layout.fillWidth: true
                
                Text {
                    text: qsTr("Administration Dashboard")
                    font.pixelSize: Theme.headlineSize
                    font.weight: Font.Bold
                    color: Theme.textColor
                    Layout.fillWidth: true
                }
                
                // User menu button
                IconButton {
                    iconSource: "qrc:/icons/user-menu.svg"
                    toolTip: qsTr("User Menu")
                    onClicked: userMenu.open()
                    
                    Menu {
                        id: userMenu
                        y: parent.height
                        
                        MenuItem {
                            text: qsTr("Switch User")
                            onTriggered: dashboardController.switchUser()
                        }
                        
                        MenuItem {
                            text: qsTr("Settings")
                            onTriggered: dashboardController.openSettings()
                        }
                        
                        MenuSeparator {}
                        
                        MenuItem {
                            text: qsTr("About")
                            onTriggered: dashboardController.showAbout()
                        }
                    }
                }
            }
            
            // Dashboard grid
            GridLayout {
                Layout.fillWidth: true
                columns: 3
                rowSpacing: Theme.spacing
                columnSpacing: Theme.spacing
                
                // Voter Search & Check-in
                CardTile {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 160
                    
                    title: qsTr("Voter Search")
                    subtitle: qsTr("Search & check-in voters")
                    iconSource: "qrc:/icons/search-voters.svg"
                    badgeVisible: dashboardController.pendingVoters > 0
                    badgeText: dashboardController.pendingVoters.toString()
                    
                    onClicked: dashboardController.openVoterSearch()
                }
                
                // Tally Counting
                CardTile {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 160
                    
                    title: qsTr("Vote Counting")
                    subtitle: qsTr("Record vote tallies")
                    iconSource: "qrc:/icons/tally-count.svg"
                    badgeVisible: dashboardController.activeSessions > 0
                    badgeText: dashboardController.activeSessions.toString()
                    badgeColor: Theme.warningColor
                    
                    onClicked: dashboardController.openTallyCounting()
                }
                
                // Turnout Reports
                CardTile {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 160
                    
                    title: qsTr("Turnout Reports")
                    subtitle: qsTr("Voting statistics")
                    iconSource: "qrc:/icons/turnout-stats.svg"
                    
                    onClicked: dashboardController.openTurnoutReports()
                }
                
                // Lebanese Tally Charts
                CardTile {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 160
                    
                    title: qsTr("Results Charts")
                    subtitle: qsTr("Bershaan & Flaan analysis")
                    iconSource: "qrc:/icons/results-charts.svg"
                    
                    onClicked: dashboardController.openResultsCharts()
                }
                
                // Candidate Winners
                CardTile {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 160
                    
                    title: qsTr("Winners")
                    subtitle: qsTr("Elected candidates")
                    iconSource: "qrc:/icons/winners.svg"
                    
                    onClicked: dashboardController.openWinners()
                }
                
                // Counting Operations
                CardTile {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 160
                    
                    title: qsTr("Count Operations")
                    subtitle: qsTr("Manage counting process")
                    iconSource: "qrc:/icons/count-ops.svg"
                    
                    onClicked: dashboardController.openCountOperations()
                }
                
                // Setup Management
                CardTile {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 160
                    
                    title: qsTr("Setup")
                    subtitle: qsTr("Parties, pens & teams")
                    iconSource: "qrc:/icons/setup.svg"
                    
                    onClicked: dashboardController.openSetup()
                }
                
                // System Settings
                CardTile {
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 160
                    
                    title: qsTr("System Settings")
                    subtitle: qsTr("App configuration")
                    iconSource: "qrc:/icons/settings.svg"
                    
                    onClicked: dashboardController.openSystemSettings()
                }
            }
            
            Item { Layout.fillHeight: true }
        }
    }
}
```

**File**: `src/JCSELECT/ui/OperatorDashboard.qml`

```qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import JCSELECT 1.0

Rectangle {
    id: root
    
    property alias controller: dashboardController
    
    color: Theme.backgroundColor
    
    DashboardController {
        id: dashboardController
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.margin * 2
        spacing: Theme.margin * 2
        
        // Header with user info
        RowLayout {
            Layout.fillWidth: true
            
            ColumnLayout {
                spacing: 4
                
                Text {
                    text: qsTr("Operator Dashboard")
                    font.pixelSize: Theme.headlineSize
                    font.weight: Font.Bold
                    color: Theme.textColor
                }
                
                Text {
                    text: qsTr("Pen: %1").arg(dashboardController.currentPenLabel)
                    font.pixelSize: Theme.bodySize
                    color: Theme.textColor
                    opacity: 0.7
                }
            }
            
            Item { Layout.fillWidth: true }
            
            // Switch user button
            IconButton {
                iconSource: "qrc:/icons/switch-user.svg"
                toolTip: qsTr("Switch User")
                onClicked: dashboardController.switchUser()
            }
        }
        
        // Two large tiles
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.margin * 2
            
            // Voter Search (Large)
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 250
                
                title: qsTr("Voter Check-in")
                subtitle: qsTr("Search and mark voters as voted")
                iconSource: "qrc:/icons/search-voters.svg"
                badgeVisible: dashboardController.pendingVoters > 0
                badgeText: dashboardController.pendingVoters.toString()
                
                onClicked: dashboardController.openVoterSearch()
            }
            
            // Tally Counting (Large)
            CardTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 250
                
                title: qsTr("Vote Counting")
                subtitle: qsTr("Record and submit vote tallies")
                iconSource: "qrc:/icons/tally-count.svg"
                badgeVisible: dashboardController.activeSessions > 0
                badgeText: dashboardController.activeSessions.toString()
                badgeColor: Theme.warningColor
                
                onClicked: dashboardController.openTallyCounting()
            }
        }
        
        // Status footer
        RowLayout {
            Layout.fillWidth: true
            
            StatusIndicator {
                status: dashboardController.syncStatus
                lastSync: dashboardController.lastSyncTime
            }
            
            Item { Layout.fillWidth: true }
            
            Text {
                text: qsTr("Total Voters: %1").arg(dashboardController.totalVoters)
                font.pixelSize: Theme.captionSize
                color: Theme.textColor
                opacity: 0.7
            }
        }
    }
}
```

### Step 6: Dashboard Controller

**File**: `src/JCSELECT/controllers/dashboard_controller.py`

```python
class DashboardController(QObject):
    """Main dashboard controller for navigation and state management"""
    
    # Signals
    navigationRequested = Signal(str)  # screen_name
    userSwitchRequested = Signal()
    
    # Properties
    pendingVoters = Property(int, notify=dataUpdated)
    activeSessions = Property(int, notify=dataUpdated)
    totalVoters = Property(int, notify=dataUpdated)
    currentPenLabel = Property(str, notify=penChanged)
    syncStatus = Property(str, notify=syncStatusChanged)
    lastSyncTime = Property('QDateTime', notify=syncStatusChanged)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_voters = 0
        self._active_sessions = 0
        self._total_voters = 0
        self._current_pen_label = ""
        self._sync_status = "offline"
        self._last_sync_time = QDateTime.currentDateTime()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_dashboard_data)
        self.update_timer.start(30000)  # Update every 30 seconds
    
    @Slot()
    def updateDashboardData(self):
        """Update dashboard statistics"""
        try:
            with get_session() as session:
                # Count pending voters
                pending_count = session.exec(
                    select(func.count(Voter.id)).where(
                        Voter.has_voted == False,
                        Voter.deleted_at.is_(None)
                    )
                ).first()
                self._pending_voters = pending_count or 0
                
                # Count active tally sessions
                active_sessions = session.exec(
                    select(func.count(TallySession.id)).where(
                        TallySession.completed_at.is_(None),
                        TallySession.deleted_at.is_(None)
                    )
                ).first()
                self._active_sessions = active_sessions or 0
                
                # Count total voters
                total_count = session.exec(
                    select(func.count(Voter.id)).where(
                        Voter.deleted_at.is_(None)
                    )
                ).first()
                self._total_voters = total_count or 0
                
                self.dataUpdated.emit()
                
        except Exception as e:
            logger.error(f"Failed to update dashboard data: {e}")
    
    # Navigation methods
    @Slot()
    def openVoterSearch(self):
        self.navigationRequested.emit("voter_search")
    
    @Slot()
    def openTallyCounting(self):
        self.navigationRequested.emit("tally_counting")
    
    @Slot()
    def openTurnoutReports(self):
        self.navigationRequested.emit("turnout_reports")
    
    @Slot()
    def openResultsCharts(self):
        self.navigationRequested.emit("results_charts")
    
    @Slot()
    def openWinners(self):
        self.navigationRequested.emit("winners")
    
    @Slot()
    def openCountOperations(self):
        self.navigationRequested.emit("count_operations")
    
    @Slot()
    def openSetup(self):
        self.navigationRequested.emit("setup")
    
    @Slot()
    def openSystemSettings(self):
        self.navigationRequested.emit("system_settings")
    
    @Slot()
    def switchUser(self):
        self.userSwitchRequested.emit()
```

### Step 7: Application Entry Points

**File**: `src/JCSELECT/admin.py`

```python
"""Admin application entry point"""
import sys
from JCSELECT.main import main
from JCSELECT.utils.auth import UserRole

def main_admin():
    """Launch jcselect in admin mode"""
    # Set environment variable to force admin mode
    import os
    os.environ["JCSELECT_MODE"] = "admin"
    os.environ["JCSELECT_REQUIRED_ROLE"] = UserRole.ADMIN.value
    
    return main()

if __name__ == "__main__":
    sys.exit(main_admin())
```

**File**: `src/JCSELECT/operator.py`

```python
"""Operator application entry point"""
import sys
from JCSELECT.main import main
from JCSELECT.utils.auth import UserRole

def main_operator():
    """Launch jcselect in operator mode"""
    # Set environment variable to force operator mode
    import os
    os.environ["JCSELECT_MODE"] = "operator"
    os.environ["JCSELECT_REQUIRED_ROLE"] = UserRole.OPERATOR.value
    
    return main()

if __name__ == "__main__":
    sys.exit(main_operator())
```

**Updated pyproject.toml**:
```toml
[tool.poetry.scripts]
jcselect = "JCSELECT.main:main"
jcselect-admin = "JCSELECT.admin:main_admin"
jcselect-operator = "JCSELECT.operator:main_operator"
```

### Step 8: Main Application Integration

**Updated File**: `src/JCSELECT/main.py`

```python
def main() -> int:
    """Initialize and run the jcselect application"""
    setup_logging()
    
    # Check application mode
    app_mode = os.environ.get("JCSELECT_MODE", "auto")
    required_role = os.environ.get("JCSELECT_REQUIRED_ROLE", None)
    
    # Set application properties
    QCoreApplication.setApplicationName("jcselect")
    QCoreApplication.setApplicationVersion("0.1.0")
    QCoreApplication.setOrganizationName("Lebanon Elections")
    
    app = QGuiApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    
    # Register QML types
    qmlRegisterType(LoginController, "JCSELECT", 1, 0, "LoginController")
    qmlRegisterType(DashboardController, "JCSELECT", 1, 0, "DashboardController")
    qmlRegisterType(PenPickerController, "JCSELECT", 1, 0, "PenPickerController")
    qmlRegisterType(VoterSearchController, "JCSELECT", 1, 0, "VoterSearchController")
    
    # Create QML engine
    engine = QQmlApplicationEngine()
    
    # Set context properties
    engine.rootContext().setContextProperty("appMode", app_mode)
    engine.rootContext().setContextProperty("requiredRole", required_role)
    
    # Set QML import paths
    ui_path = Path(__file__).parent / "ui"
    engine.addImportPath(str(ui_path))
    
    # Load main QML file
    qml_file = ui_path / "App.qml"
    engine.load(qml_file)
    
    if not engine.rootObjects():
        return 1
    
    return app.exec()
```

## 5. Execution Steps

```bash
# 1. Create authentication cache system
# Create src/JCSELECT/utils/auth_cache.py

# 2. Implement login controller
# Create src/JCSELECT/controllers/login_controller.py

# 3. Create pen picker components
# Create src/JCSELECT/ui/components/PenPickerDialog.qml
# Create src/JCSELECT/controllers/pen_picker_controller.py

# 4. Create dashboard card component
# Create src/JCSELECT/ui/components/CardTile.qml

# 5. Create dashboard layouts
# Create src/JCSELECT/ui/AdminDashboard.qml
# Create src/JCSELECT/ui/OperatorDashboard.qml

# 6. Implement dashboard controller
# Create src/JCSELECT/controllers/dashboard_controller.py

# 7. Create application entry points
# Create src/JCSELECT/admin.py
# Create src/JCSELECT/operator.py

# 8. Update main application
# Edit src/JCSELECT/main.py (add authentication flow)
# Edit src/JCSELECT/ui/App.qml (integrate login and dashboards)

# 9. Add dependencies
poetry add cryptography passlib python-jose[cryptography]

# 10. Create icon resources
# Add icon files to resources/icons/
# Update resource file

# 11. Create tests
# Create tests/unit/test_login_controller.py
# Create tests/unit/test_dashboard_controller.py
# Create tests/gui/test_login_flow.py

# 12. Test application modes
poetry run python -m JCSELECT.admin
poetry run python -m JCSELECT.operator

# 13. Run tests
poetry run pytest tests/unit/test_login_controller.py -v
poetry run pytest tests/gui/test_login_flow.py -v
```

## 6. Acceptance Criteria

- ✅ App launches to login screen on first run
- ✅ Successful login shows pen picker dialog if no pen cached
- ✅ After pen selection, appropriate dashboard loads based on user role
- ✅ Admin users see 8-tile dashboard with full functionality
- ✅ Operator users see 2-tile simplified dashboard
- ✅ Cached credentials enable automatic login on subsequent launches
- ✅ Token refresh works silently in background
- ✅ Offline login fallback works when server unavailable
- ✅ "Switch User" button clears cache and returns to login
- ✅ Dashboard tiles show live badge counts for pending items
- ✅ All UI follows Material 3 design with proper Arabic RTL support
- ✅ Application respects entry point mode (admin vs operator)
- ✅ Keyboard navigation works throughout all interfaces
- ✅ All authentication operations are logged for audit
- ✅ Invalid/expired tokens trigger re-authentication flow

This comprehensive specification provides a complete authentication and dashboard system that supports both roles while maintaining security, usability, and the Material 3 design aesthetic for Lebanese election operations.
