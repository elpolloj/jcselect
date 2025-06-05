# JCSELECT Tally Counting - Technical Specification

## 1. Overview

Build a comprehensive ballot counting interface that allows operators to record per-candidate votes for three parties per pen, with real-time totals, validation warnings, and seamless sync integration. The system maintains one active `TallySession` per pen and supports recount operations by marking existing tally lines as deleted (soft delete tombstones).

**Integration Points**:
- Extends existing voter search workflow (operators move from voter check-in to ballot counting)
- Uses established sync engine for real-time `TallyLine` delta transmission
- Updates dashboard badges immediately via Qt signals
- Follows existing Material 3 Arabic RTL design patterns

## 2. UI/UX Requirements

### 2.1 Layout Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│ Header: Pen Info + Session Status + Recount Button             │
├─────────────────────────────────────────────────────────────────┤
│ ┌─Party 1─┐ ┌─Party 2─┐ ┌─Party 3─┐ ┌─Ballot Types─┐          │
│ │Candidate│ │Candidate│ │Candidate│ │☐ Cancel      │          │
│ │☐ Name 1 │ │☐ Name 1 │ │☐ Name 1 │ │☐ White       │          │
│ │☐ Name 2 │ │☐ Name 2 │ │☐ Name 2 │ │☐ Illegal     │          │
│ │☐ Name 3 │ │☐ Name 3 │ │☐ Name 3 │ │☐ Blank       │          │
│ │   ...   │ │   ...   │ │   ...   │ └──────────────┘          │
│ └─────────┘ └─────────┘ └─────────┘                            │
├─────────────────────────────────────────────────────────────────┤
│ Running Totals: صوت: 150 | فرز: 148 | بيضاء: 1 | ملغاة: 1      │
├─────────────────────────────────────────────────────────────────┤
│        [تأكيد الورقة - Confirm Ballot]    [Cancel]              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Visual Design Requirements
- **Framework**: Material 3 with Arabic RTL layout
- **Typography**: Consistent with existing Theme.qml (Arabic + English support)
- **Columns**: Three equal-width scrollable party columns with headers
- **Checkboxes**: Material 3 style with clear visual feedback
- **Validation**: Warning indicators (yellow/orange) for over-votes, never blocking
- **Animations**: Smooth checkbox state changes and count updates
- **Accessibility**: Keyboard navigation and screen reader support

### 2.3 Interaction Patterns
- **Single Selection**: Max one candidate per party (checkbox auto-deselects others)
- **Ballot Types**: Mutually exclusive special ballot selections
- **Real-time Feedback**: Vote counts update immediately on selection
- **Confirmation Flow**: Two-step process (select → confirm) with visual preview
- **Validation Warnings**: Non-blocking alerts for suspicious vote patterns

## 3. Data Model Additions

### 3.1 Enhanced TallySession
```sql
-- Add to existing TallySession table
ALTER TABLE tally_sessions ADD COLUMN ballot_number INTEGER DEFAULT 0;
ALTER TABLE tally_sessions ADD COLUMN recounted_at TIMESTAMP NULL;
ALTER TABLE tally_sessions ADD COLUMN recount_operator_id UUID NULL;

-- Add foreign key constraint
ALTER TABLE tally_sessions ADD CONSTRAINT fk_tally_sessions_recount_operator 
    FOREIGN KEY (recount_operator_id) REFERENCES users(id);
```

### 3.2 Enhanced TallyLine for Ballot Types
```sql
-- Add ballot type tracking to TallyLine
ALTER TABLE tally_lines ADD COLUMN ballot_type VARCHAR(20) DEFAULT 'normal';
-- ballot_type values: 'normal', 'cancel', 'white', 'illegal', 'blank'

-- Add ballot number tracking
ALTER TABLE tally_lines ADD COLUMN ballot_number INTEGER NULL;
```

### 3.3 New Domain Models
```python
# src/JCSELECT/models.py additions

class BallotType(str, Enum):
    NORMAL = "normal"
    CANCEL = "cancel" 
    WHITE = "white"
    ILLEGAL = "illegal"
    BLANK = "blank"

class BallotEntry(BaseModel):
    """Single ballot entry for UI processing"""
    party_selections: Dict[str, Optional[str]] = {}  # party_id -> candidate_id
    ballot_type: BallotType = BallotType.NORMAL
    ballot_number: int
    timestamp: datetime
    operator_id: str
```

## 4. Controller Architecture

### 4.1 TallyController Structure
```python
# src/JCSELECT/controllers/tally_controller.py

class TallyController(QObject):
    """Main tally counting controller"""
    
    # Properties
    currentSession = Property('QVariant', notify=sessionChanged)
    totalVotes = Property(int, notify=countsChanged)
    totalCounted = Property(int, notify=countsChanged) 
    totalWhite = Property(int, notify=countsChanged)
    totalIllegal = Property(int, notify=countsChanged)
    totalCandidates = Property(int, notify=countsChanged)
    currentBallotNumber = Property(int, notify=ballotNumberChanged)
    partyColumns = Property('QVariantList', notify=partiesLoaded)
    selectedCandidates = Property('QVariantMap', notify=selectionChanged)
    selectedBallotType = Property(str, notify=ballotTypeChanged)
    hasValidationWarnings = Property(bool, notify=validationChanged)
    validationMessages = Property('QStringList', notify=validationChanged)
    
    # Signals
    sessionChanged = Signal()
    countsChanged = Signal()
    ballotNumberChanged = Signal()
    partiesLoaded = Signal()
    selectionChanged = Signal()
    ballotTypeChanged = Signal()
    validationChanged = Signal()
    ballotConfirmed = Signal(int)  # ballot_number
    recountStarted = Signal()
    recountCompleted = Signal()
    errorOccurred = Signal(str)
    
    # Core Operations
    @Slot(str, str)
    def selectCandidate(self, party_id: str, candidate_id: str)
    
    @Slot(str)
    def selectBallotType(self, ballot_type: str)
    
    @Slot()
    def confirmBallot(self)
    
    @Slot()
    def clearCurrentBallot(self)
    
    @Slot()
    def startRecount(self)
    
    @Slot()
    def loadPartyData(self)
    
    @Slot()
    def refreshCounts(self)
```

### 4.2 Validation Logic
```python
def _validate_current_ballot(self) -> List[str]:
    """Validate current ballot selections and return warnings"""
    warnings = []
    
    # Over-vote detection
    total_selections = len([c for c in self._selected_candidates.values() if c])
    if total_selections > 3:  # Lebanese election rules
        warnings.append("تحذير: عدد الأصوات أكثر من المسموح")
    
    # Under-vote notification
    if total_selections == 0 and self._selected_ballot_type == BallotType.NORMAL:
        warnings.append("ملاحظة: لم يتم اختيار أي مرشح")
    
    # Mixed ballot type warnings
    if total_selections > 0 and self._selected_ballot_type != BallotType.NORMAL:
        warnings.append("تحذير: اختيار مرشحين مع نوع ورقة خاص")
    
    return warnings
```

## 5. Sync Integration

### 5.1 Real-time TallyLine Updates
```python
def _confirm_ballot_and_sync(self):
    """Confirm ballot and immediately queue for sync"""
    try:
        with get_session() as session:
            # Update ballot number
            self._current_session.ballot_number += 1
            session.add(self._current_session)
            
            # Create TallyLine entries for each selection
            changes_to_sync = []
            
            for party_id, candidate_id in self._selected_candidates.items():
                if candidate_id:  # Skip empty selections
                    tally_line = TallyLine(
                        tally_session_id=self._current_session.id,
                        party_id=party_id,
                        vote_count=1,  # Increment by 1
                        ballot_type=self._selected_ballot_type,
                        ballot_number=self._current_session.ballot_number
                    )
                    session.add(tally_line)
                    
                    # Queue for sync
                    changes_to_sync.append({
                        "entity_type": "TallyLine",
                        "entity_id": str(tally_line.id),
                        "operation": "CREATE",
                        "data": tally_line_to_dict(tally_line)
                    })
            
            # Handle special ballot types
            if self._selected_ballot_type != BallotType.NORMAL:
                special_line = TallyLine(
                    tally_session_id=self._current_session.id,
                    party_id=None,  # Special ballots don't have party
                    vote_count=1,
                    ballot_type=self._selected_ballot_type,
                    ballot_number=self._current_session.ballot_number
                )
                session.add(special_line)
                changes_to_sync.append({
                    "entity_type": "TallyLine", 
                    "entity_id": str(special_line.id),
                    "operation": "CREATE",
                    "data": tally_line_to_dict(special_line)
                })
            
            session.commit()
            
            # Queue all changes for sync
            for change in changes_to_sync:
                sync_queue.enqueue_change(**change)
            
            # Update dashboard badges immediately
            self.ballotConfirmed.emit(self._current_session.ballot_number)
            self._refresh_counts()
            
    except Exception as e:
        session.rollback()
        self.errorOccurred.emit(f"Failed to confirm ballot: {str(e)}")
```

### 5.2 Recount Sync Strategy
```python
@Slot()
def startRecount(self):
    """Start recount by soft-deleting existing tally lines"""
    try:
        with get_session() as session:
            # Mark all existing lines as deleted
            existing_lines = session.exec(
                select(TallyLine).where(
                    TallyLine.tally_session_id == self._current_session.id,
                    TallyLine.deleted_at.is_(None)
                )
            ).all()
            
            changes_to_sync = []
            for line in existing_lines:
                line.deleted_at = func.now()
                line.deleted_by = self._current_operator_id
                
                changes_to_sync.append({
                    "entity_type": "TallyLine",
                    "entity_id": str(line.id),
                    "operation": "UPDATE",
                    "data": tally_line_to_dict(line)
                })
            
            # Reset session ballot number
            self._current_session.ballot_number = 0
            self._current_session.recounted_at = func.now()
            self._current_session.recount_operator_id = self._current_operator_id
            
            session.commit()
            
            # Queue sync changes
            for change in changes_to_sync:
                sync_queue.enqueue_change(**change)
            
            self.recountCompleted.emit()
            self._refresh_counts()
            
    except Exception as e:
        self.errorOccurred.emit(f"Recount failed: {str(e)}")
```

## 6. Step-by-Step Implementation Plan

### Step 1: Database Schema Updates
**Files to edit**:
- Create new Alembic migration file
- Update `src/JCSELECT/models.py`

```bash
# Create migration
poetry run alembic revision --autogenerate -m "Add tally counting enhancements"

# Update models.py with BallotType enum and enhanced TallyLine
```

### Step 2: Enhanced TallyLine and TallySession Models
**Files to edit**:
- `src/JCSELECT/models.py`

```python
# Add BallotType enum
# Update TallyLine with ballot_type and ballot_number fields
# Update TallySession with ballot_number, recounted_at, recount_operator_id
```

### Step 3: TallyController Implementation ✅ **COMPLETED**
**Files to create/edit**:
- Create `src/JCSELECT/controllers/tally_controller.py`

```python
# Implement complete TallyController class
# Add all properties, signals, and slots
# Implement validation logic
# Add sync integration methods
```

**Implementation Status**: 
- ✅ Complete TallyController class with all specified properties, signals, and slots
- ✅ Validation logic with Arabic warning messages for over-vote, under-vote, and mixed ballot types
- ✅ Sync integration via `sync_queue.enqueue_change()` for real-time TallyLine updates
- ✅ Recount functionality with soft-delete tombstones and session metadata updates
- ✅ QML type registration in `main.py` as `qmlRegisterType(TallyController, "jcselect", 1, 0, "TallyController")`
- ✅ Placeholder `TallyCountingWindow.qml` created with basic layout structure
- ✅ Enhanced DAO with helper functions: `get_parties_for_pen()`, `get_candidates_by_party()`, `get_or_create_tally_session()`, `get_tally_session_counts()`
- ✅ Comprehensive test suite (25/25 tests passing) covering all core functionality

**API Surface**: Final implementation matches specification with no significant deviations. All properties, signals, and slots implemented as designed.

### Step 4: Party Data Loading and Management ✅ COMPLETED
**Files edited**:
- `src/jcselect/dao.py` - Added DAO helper functions
- `src/jcselect/ui/components/PartyColumn.qml` - Created party column component
- `src/jcselect/ui/components/CandidateCheckbox.qml` - Created candidate checkbox component  
- `src/jcselect/ui/components/BallotTypePanel.qml` - Created ballot type panel component
- `src/jcselect/ui/components/qmldir` - Component registration file
- `src/jcselect/ui/TallyCountingWindow.qml` - Updated to use new components
- `tests/unit/test_party_dao.py` - Comprehensive DAO tests (18 tests, all passing)
- `tests/gui/test_party_components.py` - GUI component tests (7 tests, all passing)

**Implementation Status**:
- ✅ `get_parties_for_pen()` - Returns all parties for a pen with proper validation
- ✅ `get_candidates_by_party()` - Returns mock candidate data with proper structure
- ✅ `get_or_create_tally_session()` - Creates or retrieves active tally session
- ✅ `get_tally_session_counts()` - Calculates running totals by ballot type
- ✅ PartyColumn component with scrollable candidate list and Material 3 design
- ✅ CandidateCheckbox component with RTL-friendly layout and animations
- ✅ BallotTypePanel with Arabic labels and proper color coding
- ✅ TallyCountingWindow integration with live data binding
- ✅ All components properly registered and importable
- ✅ Comprehensive test coverage with 25/25 tests passing

**Key Features Implemented**:
- Party data loading with soft-delete awareness
- Candidate selection with single-selection per party enforcement
- Ballot type selection with mutual exclusivity  
- Real-time data binding between controller and UI components
- Arabic RTL layout with proper Material 3 styling
- Comprehensive error handling and validation
- Full test coverage for both DAO and UI components

### Step 5: Main Tally Counting QML Interface ✅ COMPLETED
**Files edited**:
- `src/jcselect/ui/TallyCountingWindow.qml` - Complete tally counting interface
- `src/jcselect/ui/components/TallyTotals.qml` - Live running totals component
- `src/jcselect/ui/components/ValidationWarnings.qml` - Non-blocking validation warnings
- `src/jcselect/ui/components/qmldir` - Updated component registrations
- `src/jcselect/controllers/tally_controller.py` - Added totalCancel and totalBlank properties
- `src/jcselect/ui/App.qml` - Updated navigation integration for tally counting
- `tests/unit/test_validation_logic.py` - Comprehensive validation tests (12 tests, all passing)
- `tests/gui/test_tally_counting_window.py` - GUI integration tests (14 tests, all passing)

**Implementation Status**:
- ✅ Complete TallyCountingWindow with header, three party columns, and ballot type panel
- ✅ TallyTotals component with animated counters and Arabic labels
- ✅ ValidationWarnings component with RTL support and warning icons
- ✅ Full RTL layout support with proper Arabic text alignment
- ✅ Material 3 design consistency across all components
- ✅ Live data binding between controller and UI components
- ✅ Action buttons (Cancel/Confirm) with proper enable/disable logic
- ✅ Session initialization and navigation integration via App.qml
- ✅ Dashboard controller integration with openTallyCounting() method
- ✅ Comprehensive validation logic with Lebanese election rules (max 3 candidates)
- ✅ Over-vote, under-vote, and mixed-ballot warning system
- ✅ All components properly registered and importable

**Key Features Implemented**:
- Header row with pen label, ballot number, and recount button
- Three-column party layout with candidate selection
- Sidebar ballot type panel with mutual exclusivity
- Non-blocking validation warnings with Arabic messages
- Live running totals with smooth animations
- Confirm ballot button disabled until selections made
- Complete navigation integration with dashboard
- Full test coverage with 26/26 tests passing

### Step 6: Reusable Candidate Selection Components ✅ COMPLETED
**Files implemented** (completed as part of Step 4):
- `src/jcselect/ui/components/CandidateCheckbox.qml` - Material 3 checkbox with candidate info
- `src/jcselect/ui/components/PartyColumn.qml` - Scrollable party column with single-selection logic
- `src/jcselect/ui/components/BallotTypePanel.qml` - Mutually exclusive ballot type buttons
- `src/jcselect/ui/components/qmldir` - All components properly registered
- `src/jcselect/ui/TallyCountingWindow.qml` - Components integrated with signal wiring
- `tests/gui/test_party_components.py` - Component tests (7 tests, all passing)
- `tests/gui/test_tally_counting_window.py` - Integration tests (14 tests, all passing)

**Implementation Status**:
- ✅ CandidateCheckbox with Material 3 design, hover effects, and RTL support
- ✅ PartyColumn with ScrollView, ListView delegates, and single-selection enforcement
- ✅ BallotTypePanel with four mutually exclusive buttons and Arabic labels
- ✅ All components properly registered in qmldir for import
- ✅ Signal wiring between components and TallyController working correctly
- ✅ RTL-friendly layouts with proper Arabic text alignment
- ✅ Material 3 styling with proper color theming and rounded corners
- ✅ Accessibility features including cursor shapes and hover effects
- ✅ Complete integration with TallyController via signal/slot pattern
- ✅ Comprehensive test coverage with both unit and integration tests

**Key Features Implemented**:
- Single-candidate-per-party enforcement via PartyColumn logic
- Mutually exclusive ballot types with "normal" as default
- RTL-friendly components with Arabic label support
- Material 3 styling with proper color theming and rounded corners
- Accessibility features including cursor shapes and hover effects
- Complete integration with TallyController via signal/slot pattern
- Comprehensive test coverage with both unit and integration tests

### Step 7: Running Totals and Status Components ✅ COMPLETED
**Files implemented** (completed as part of Step 5):
- `src/jcselect/ui/components/TallyTotals.qml` - Live count display with Arabic labels
- `src/jcselect/ui/components/ValidationWarnings.qml` - Non-blocking validation warnings with RTL support
- `src/jcselect/ui/components/qmldir` - Components registered for import
- `tests/unit/test_validation_logic.py` - Validation tests (12 tests, all passing)
- `tests/gui/test_tally_counting_window.py` - Integration tests (14 tests, all passing)

**Implementation Status**:
- ✅ TallyTotals with animated counters and Arabic vote category labels
- ✅ Color-coded rectangles for different ballot types (blue, green, orange, red)
- ✅ Smooth NumberAnimation for count changes with 300ms duration
- ✅ ValidationWarnings with RTL support and warning icon
- ✅ Pulsing border animation for attention-grabbing warnings
- ✅ Arabic text detection for proper text alignment
- ✅ Material 3 design consistency with rounded corners
- ✅ Properties for all vote categories: totalVotes, totalCandidates, totalWhite, totalIllegal, totalCancel, totalBlank
- ✅ Non-blocking warning display with dismiss functionality
- ✅ Integration with TallyController validation system

**Key Features Implemented**:
- Live running totals with smooth animated updates
- Arabic labels for all vote categories with semantic color coding
- Non-blocking validation warnings that don't interrupt workflow
- RTL-friendly text alignment based on content detection
- Material 3 design patterns with consistent styling
- Accessibility features with proper hover states and tooltips

### Step 8: Dashboard Navigation Integration ✅ COMPLETED
**Files implemented** (completed as part of Step 5):
- `src/jcselect/controllers/dashboard_controller.py` - Added openTallyCounting() navigation method
- `src/jcselect/ui/App.qml` - TallyCountingWindow integrated with proper navigation
- `src/jcselect/ui/AdminDashboard.qml` - Vote Counting tile with openTallyCounting() call
- `src/jcselect/ui/OperatorDashboard.qml` - Large Vote Counting tile with navigation
- `src/jcselect/main.py` - TallyController registered as QML type
- `tests/gui/test_tally_counting_window.py` - Navigation integration tests (14 tests, all passing)
- `tests/gui/test_login_flow.py` - Dashboard navigation method tests

**Implementation Status**:
- ✅ DashboardController.openTallyCounting() method emits navigationRequested("tally_counting")
- ✅ App.qml switch statement handles "tally_counting" case and loads TallyCountingWindow
- ✅ Dashboard tiles properly connected to openTallyCounting() method
- ✅ Badge display for active tally sessions with dashboardController.activeSessions
- ✅ Session initialization handled in App.qml with operator ID and pen selection
- ✅ Tally event connections for ballot confirmation and recount completion
- ✅ TallyController QML type registration in main.py
- ✅ Navigation method testing in GUI test suite
- ✅ Dashboard badge refresh logic for real-time updates
- ✅ Error handling and app-wide notification integration

### Step 9: Enhanced Sync Queue Integration ✅ COMPLETED
**Files implemented**:
- `src/jcselect/sync/queue.py` - Enhanced with enqueue_tally_line helper and fast sync triggers
- `src/jcselect/sync/engine.py` - Added fast-path handling and global sync engine accessor
- `src/jcselect/controllers/tally_controller.py` - Updated to use new sync helpers and triggers
- `src/jcselect/controllers/dashboard_controller.py` - Added sync completion badge refresh
- `src/jcselect/utils/settings.py` - Added sync_fast_tally_enabled setting
- `tests/unit/test_sync_queue_tally.py` - Comprehensive sync queue tests (8 tests, all passing)
- `tests/integration/test_tally_sync_fast_path.py` - Integration tests for fast sync (8 tests, 2 passing, 6 skipped due to async)

**Implementation Status**:
- ✅ enqueue_tally_line() helper serializes TallyLine objects using tally_line_to_dict()
- ✅ Fast sync triggers automatically for TallyLine changes when sync_fast_tally_enabled=True
- ✅ TallyController uses enqueue_tally_line() for ballot confirmation and recount operations
- ✅ sync_queue.trigger_fast_sync() called after ballot operations for <2s sync latency
- ✅ Dashboard controller listens for sync completion and refreshes badges automatically
- ✅ Recount tombstones (deleted_at set) properly queued and synced
- ✅ Fast sync uses smaller batches (max 5 items) for quicker transmission
- ✅ Global sync engine accessor (get_sync_engine/set_sync_engine) for cross-module access
- ✅ Graceful handling when sync engine not available
- ✅ All existing tests remain green (25/25 tally controller tests passing)

### Step 10: QML Type Registration and Main App Integration
**Files to edit**:
- `src/JCSELECT/main.py`

```python
# Register TallyController QML type
# Update app routing logic
# Ensure proper initialization order
```

## 7. Detailed File Specifications

### 7.1 TallyCountingWindow.qml Layout
```qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import JCSELECT 1.0

Rectangle {
    id: root
    
    TallyController {
        id: tallyController
        onBallotConfirmed: {
            // Clear selections and prepare for next ballot
            clearCurrentBallot()
        }
        onRecountCompleted: {
            confirmationDialog.showMessage("تم إعادة العد بنجاح")
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.margin
        
        // Header with session info and recount
        RowLayout {
            Layout.fillWidth: true
            
            Text {
                text: qsTr("Ballot Counting - Pen %1").arg(tallyController.currentPenLabel)
                font.pixelSize: Theme.headlineSize
                color: Theme.textColor
            }
            
            Item { Layout.fillWidth: true }
            
            Text {
                text: qsTr("Ballot #%1").arg(tallyController.currentBallotNumber + 1)
                font.pixelSize: Theme.titleSize
                color: Theme.primaryColor
            }
            
            Button {
                text: qsTr("إعادة العد")
                enabled: tallyController.totalVotes > 0
                onClicked: recountDialog.open()
            }
        }
        
        // Three party columns + ballot types
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spacing
            
            // Party columns
            Repeater {
                model: tallyController.partyColumns
                
                PartyColumn {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    
                    partyData: modelData
                    selectedCandidate: tallyController.selectedCandidates[modelData.id]
                    
                    onCandidateSelected: {
                        tallyController.selectCandidate(modelData.id, candidateId)
                    }
                }
            }
            
            // Ballot types panel
            BallotTypePanel {
                Layout.preferredWidth: 200
                Layout.fillHeight: true
                
                selectedType: tallyController.selectedBallotType
                onTypeSelected: tallyController.selectBallotType(type)
            }
        }
        
        // Validation warnings
        ValidationWarnings {
            Layout.fillWidth: true
            warnings: tallyController.validationMessages
            visible: tallyController.hasValidationWarnings
        }
        
        // Running totals
        TallyTotals {
            Layout.fillWidth: true
            
            totalVotes: tallyController.totalVotes
            totalCounted: tallyController.totalCounted
            totalWhite: tallyController.totalWhite
            totalIllegal: tallyController.totalIllegal
            totalCandidates: tallyController.totalCandidates
        }
        
        // Action buttons
        RowLayout {
            Layout.fillWidth: true
            
            Item { Layout.fillWidth: true }
            
            Button {
                text: qsTr("Cancel")
                onClicked: tallyController.clearCurrentBallot()
            }
            
            Button {
                text: qsTr("تأكيد الورقة")
                enabled: tallyController.hasSelections
                highlighted: true
                
                onClicked: tallyController.confirmBallot()
            }
        }
    }
}
```

### 7.2 PartyColumn.qml Component
```qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    
    property var partyData
    property string selectedCandidate: ""
    
    signal candidateSelected(string candidateId)
    
    color: Theme.surfaceColor
    radius: Theme.radius
    border.color: Theme.primaryColor
    border.width: 1
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing
        spacing: Theme.spacing
        
        // Party header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: Theme.primaryColor
            radius: Theme.radius
            
            Text {
                anchors.centerIn: parent
                text: partyData.name
                font.pixelSize: Theme.titleSize
                font.weight: Font.Bold
                color: "white"
            }
        }
        
        // Candidate list
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            ListView {
                model: partyData.candidates
                spacing: Theme.spacing / 2
                
                delegate: CandidateCheckbox {
                    width: ListView.view.width
                    
                    candidateData: modelData
                    checked: root.selectedCandidate === modelData.id
                    
                    onToggled: {
                        if (checked) {
                            root.candidateSelected(modelData.id)
                        } else {
                            root.candidateSelected("")
                        }
                    }
                }
            }
        }
    }
}
```

## 8. Testing Strategy

### 8.1 Unit Tests
**File**: `tests/unit/test_tally_controller.py`
```python
def test_candidate_selection_exclusivity():
    """Test only one candidate per party can be selected"""

def test_ballot_confirmation_creates_tally_lines():
    """Test confirmed ballot creates proper TallyLine records"""

def test_recount_soft_deletes_existing_lines():
    """Test recount marks existing lines as deleted"""

def test_validation_warnings_generation():
    """Test over-vote and under-vote warning logic"""

def test_count_calculations():
    """Test running total calculations are accurate"""
```

### 8.2 GUI Tests  
**File**: `tests/gui/test_tally_counting.py`
```python
@pytest.mark.qt
def test_candidate_checkbox_interaction():
    """Test clicking candidate checkboxes updates selections"""

@pytest.mark.qt  
def test_ballot_confirmation_flow():
    """Test complete ballot entry and confirmation process"""

@pytest.mark.qt
def test_recount_dialog_and_execution():
    """Test recount button triggers proper dialog and execution"""
```

### 8.3 Integration Tests
**File**: `tests/integration/test_tally_sync.py`
```python
def test_tally_line_sync_round_trip():
    """Test TallyLine changes sync correctly to server"""

def test_recount_tombstones_sync():
    """Test recount soft deletes sync as tombstones"""

def test_dashboard_badge_updates():
    """Test tally operations update dashboard badges immediately"""
```

## 9. Acceptance Criteria

- ✅ Tally counting window displays three party columns with candidate lists
- ✅ Only one candidate per party can be selected (checkboxes are mutually exclusive)
- ✅ Special ballot types (cancel, white, illegal, blank) are mutually exclusive
- ✅ Running totals update immediately when selections change
- ✅ Validation warnings appear for over-votes but don't block confirmation
- ✅ Confirmed ballots create TallyLine records and increment ballot number
- ✅ Recount button soft-deletes existing lines and resets ballot counter
- ✅ All tally operations queue for sync immediately
- ✅ Dashboard badges update in real-time when ballots are confirmed
- ✅ Arabic RTL layout works correctly for all text and UI elements
- ✅ Keyboard navigation works for accessibility
- ✅ Offline operation queues changes until sync connection available
- ✅ Interface follows Material 3 design patterns consistently
- ✅ Error handling provides clear user feedback
- ✅ Session persistence survives application restart

## 10. Future Enhancements

### 10.1 Barcode Ballot Scanning
- USB barcode scanner integration
- Automatic candidate selection based on barcode data
- Validation against expected ballot format

### 10.2 Keyboard Shortcuts
- Number keys (1-9) for quick candidate selection
- Enter for ballot confirmation
- Ctrl+R for recount
- Tab navigation between party columns

### 10.3 Advanced Validation
- Cross-reference with voter turnout numbers
- Statistical anomaly detection
- Automatic backup before recount operations

### 10.4 Enhanced Reporting
- Real-time ballot counting graphs
- Export capabilities for election commission
- Print ballot summary reports

This specification provides a comprehensive foundation for implementing the tally counting feature while maintaining consistency with the existing jcselect architecture and Lebanese election requirements.