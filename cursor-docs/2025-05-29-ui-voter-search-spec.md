
# JCSELECT Voter Search & Check-in - Technical Specification

## 1. Overview

Build the first user-facing screen of jcselect: a **Voter Search & Check-in** window that allows operators to search voters by number or name, view voter details with voting status, and mark voters as voted through an intuitive Arabic RTL interface.

## 2. Technical Requirements

### 2.1 UI Framework & Design
- **Framework**: PySide 6/QML with Qt 6.x
- **Design System**: Material 3 design language
- **Layout**: Arabic RTL by default with proper text mirroring
- **Typography**: Support for Arabic and English fonts
- **Performance**: Search filtering under 100ms for datasets up to 1000 voters
- **Responsiveness**: Adaptive layout for different window sizes (1200x800 minimum)

### 2.2 Functional Requirements
- **Search Capabilities**: Real-time search by voter number (exact/partial) and name (fuzzy)
- **Results Display**: Virtualized list view for performance with large datasets
- **Voter Actions**: Single-click voter marking with confirmation feedback
- **Status Tracking**: Visual indicators for voted/not voted status
- **User Feedback**: Toast notifications for successful actions
- **Keyboard Shortcuts**: Ctrl+F for search focus, Enter for quick actions

### 2.3 Data Integration
- **Offline Operation**: Direct DAO layer integration for immediate database access
- **Real-time Updates**: UI updates without page refresh after voter marking
- **Data Transfer Objects**: Lightweight DTOs for UI-controller communication
- **Error Handling**: Graceful handling of database errors and edge cases

## 3. Architecture Design

### 3.1 Component Architecture
```
VoterSearchWindow.qml
├── SearchBar.qml (search input + filters)
├── VoterResultsList.qml (virtualized ListView)
│   └── VoterCard.qml (individual voter display)
├── VoterDetailPane.qml (selected voter details)
│   └── VoteButton.qml ("تم" marking button)
└── Snackbar.qml (feedback notifications)
```

### 3.2 Controller Pattern
```
VoterSearchController (QObject)
├── Properties: searchQuery, selectedVoter, searchResults
├── Signals: searchResultsChanged, voterMarked, errorOccurred
├── Slots: performSearch, selectVoter, markVoterAsVoted
└── Private: _dao_operations, _search_logic, _validation
```

### 3.3 Data Flow
```
User Input → Controller → DAO → Database
                ↓
QML UI ← Signals ← Controller ← DAO Response
```

## 4. Detailed Implementation Plan

### Step 1: Extend Theme System

**File**: `src/JCSELECT/ui/Theme.qml`

**Additions Required**:
- Material 3 color tokens (primary, secondary, tertiary variants)
- Elevation and shadow definitions (0dp, 1dp, 2dp, 3dp, 6dp)
- Typography scale (display, headline, title, label, body variants)
- Component-specific spacing and sizing tokens
- Animation duration and easing curve constants
- RTL-aware margin and padding helpers

**New Properties**:
```qml
// Material 3 Color System
readonly property color primaryContainer: "#E8DEF8"
readonly property color onPrimaryContainer: "#21005D"
readonly property color secondaryContainer: "#E8DEF8"
readonly property color errorContainer: "#FFDAD6"
readonly property color successContainer: "#D1FFCA"

// Elevation Tokens
readonly property color elevation1: "#F7F2FA"
readonly property color elevation2: "#F3EDF7"
readonly property color elevation3: "#EFEBF4"

// Typography
readonly property int displayLarge: 36
readonly property int headlineMedium: 24
readonly property int titleLarge: 22
readonly property int labelLarge: 14

// Component Sizing
readonly property int searchBarHeight: 56
readonly property int cardMinHeight: 72
readonly property int buttonHeight: 40
readonly property int snackbarHeight: 48
```

### Step 2: Create Reusable QML Components

**File Structure**:
```
src/JCSELECT/ui/components/
├── SearchBar.qml
├── VoterCard.qml
├── VoterDetailPane.qml
├── VoteButton.qml
├── Snackbar.qml
└── qmldir
```

**SearchBar.qml Specification**:
- Rounded Rectangle container with Material 3 styling
- TextInput with placeholder text in Arabic
- Search icon (magnifying glass) on the right side (RTL)
- Clear button (X) when text is present
- Focus handling with keyboard shortcuts (Ctrl+F)
- Real-time text change signals
- Loading indicator during search operations

**VoterCard.qml Specification**:
- Card container with subtle elevation shadow
- Voter information layout: name, number, father/mother names
- Voting status badge (green checkmark or pending indicator)
- Hover and selection states with visual feedback
- RTL text alignment and proper Arabic typography
- Click handling for selection
- Accessibility support with proper roles

**VoterDetailPane.qml Specification**:
- Detailed voter information display
- Large, prominent voting action area
- Vote timestamp display (if already voted)
- Operator information (who marked the voter)
- Responsive layout for different content sizes
- Integration with VoteButton component

**VoteButton.qml Specification**:
- Large, accessible button with Arabic text "تم ✅"
- Material 3 filled button styling
- Loading state during vote processing
- Disabled state for already-voted voters
- Confirmation animation on successful vote
- Error state handling

**Snackbar.qml Specification**:
- Bottom-aligned notification container
- Auto-dismiss after configurable timeout (default 2s)
- Slide-in/out animations
- Success, error, and info variants
- Arabic text support with proper alignment
- Action button support (optional)

### Step 3: Data Transfer Objects

**File**: `src/JCSELECT/models/dto.py`

**VoterDTO Class**:
```python
@dataclass
class VoterDTO:
    id: str
    voter_number: str
    full_name: str
    father_name: str | None
    mother_name: str | None
    pen_label: str
    has_voted: bool
    voted_at: datetime | None
    voted_by_operator: str | None
    
    @property
    def display_name(self) -> str:
        """Formatted name for UI display"""
    
    @property
    def search_text(self) -> str:
        """Concatenated searchable text"""
```

**SearchResultDTO Class**:
```python
@dataclass
class SearchResultDTO:
    voters: List[VoterDTO]
    total_count: int
    search_query: str
    execution_time_ms: int
```

### Step 4: Voter Search Controller Implementation

**File**: `src/JCSELECT/controllers/voter_search_controller.py`

**Core Functionality**:
- Search query management with debouncing (300ms delay)
- Real-time search execution with performance monitoring
- Voter selection state management
- Vote marking with audit trail integration
- Error handling with user-friendly messages
- Loading state management

**QML-Exposed Properties**:
```python
class VoterSearchController(QObject):
    # Properties
    searchQuery = Property(str, notify=searchQueryChanged)
    selectedVoter = Property('QVariant', notify=selectedVoterChanged)
    searchResults = Property('QVariantList', notify=searchResultsChanged)
    isLoading = Property(bool, notify=isLoadingChanged)
    errorMessage = Property(str, notify=errorMessageChanged)
```

**Signal Definitions**:
```python
# Signals
searchQueryChanged = Signal()
selectedVoterChanged = Signal()
searchResultsChanged = Signal()
isLoadingChanged = Signal()
errorMessageChanged = Signal()
voterMarkedSuccessfully = Signal(str)  # voter name
operationFailed = Signal(str)  # error message
```

**Core Methods**:
```python
@Slot(str)
def setSearchQuery(self, query: str) -> None:
    """Update search query with debouncing"""

@Slot(str)
def selectVoter(self, voter_id: str) -> None:
    """Select voter for detailed view"""

@Slot(str, str)
def markVoterAsVoted(self, voter_id: str, operator_id: str) -> None:
    """Mark voter as voted with error handling"""

@Slot()
def clearSelection(self) -> None:
    """Clear selected voter"""

@Slot()
def refreshSearch(self) -> None:
    """Re-execute current search"""
```

### Step 5: Search Logic Implementation

**Search Algorithm Requirements**:
- **Exact Number Matching**: Voter number exact match (highest priority)
- **Partial Number Matching**: Voter number starts-with matching
- **Name Fuzzy Matching**: Full name and father/mother name fuzzy search
- **Arabic Text Handling**: Proper Arabic character normalization
- **Performance Optimization**: Database indexing and query optimization
- **Result Ranking**: Relevance-based result ordering

**Implementation Details**:
```python
def _build_search_query(self, query: str) -> Select:
    """Build optimized SQL query for search"""
    # Normalize Arabic text
    normalized_query = self._normalize_arabic_text(query)
    
    # Build compound query with relevance scoring
    exact_number = Voter.voter_number == query
    partial_number = Voter.voter_number.startswith(query)
    name_match = Voter.full_name.contains(normalized_query)
    father_match = Voter.father_name.contains(normalized_query)
    
    return select(Voter).where(
        or_(exact_number, partial_number, name_match, father_match)
    ).order_by(
        case(
            (exact_number, 1),
            (partial_number, 2),
            (name_match, 3),
            else_=4
        )
    ).limit(100)
```

### Step 6: Main UI Integration

**File**: `src/JCSELECT/ui/VoterSearchWindow.qml`

**Layout Structure**:
```qml
ColumnLayout {
    SearchBar {
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.searchBarHeight
    }
    
    RowLayout {
        ListView {
            // Voter results list
            Layout.fillHeight: true
            Layout.preferredWidth: parent.width * 0.6
        }
        
        VoterDetailPane {
            Layout.fillHeight: true
            Layout.fillWidth: true
        }
    }
    
    Snackbar {
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.snackbarHeight
    }
}
```

**Performance Optimizations**:
- ListView with virtualization enabled (`cacheBuffer`, `displayMarginBeginning`)
- Asynchronous image loading for voter photos (future)
- Debounced search input handling
- Lazy loading for large result sets
- Memory-efficient delegate recycling

### Step 7: Update Main Application

**File**: `src/JCSELECT/ui/App.qml`

**Changes Required**:
- Replace placeholder Rectangle with VoterSearchWindow
- Add VoterSearchController instantiation
- Set up global keyboard shortcuts
- Configure window properties for optimal UX
- Add application state management

**Integration Code**:
```qml
VoterSearchController {
    id: voterController
}

VoterSearchWindow {
    anchors.fill: parent
    controller: voterController
}

Shortcut {
    sequence: "Ctrl+F"
    onActivated: voterController.focusSearchBar()
}
```

### Step 8: Database Query Optimization

**Required Database Changes**:
- Add indexes on frequently searched columns
- Optimize search query performance
- Add full-text search capabilities (if needed)
- Implement query result caching

**Index Additions** (via Alembic migration):
```sql
CREATE INDEX idx_voter_number ON voter(voter_number);
CREATE INDEX idx_voter_full_name ON voter(full_name);
CREATE INDEX idx_voter_father_name ON voter(father_name);
CREATE INDEX idx_voter_search_composite ON voter(voter_number, full_name);
```

### Step 9: Testing Implementation

**File**: `tests/unit/test_voter_search_controller.py`

**Test Coverage**:
- Search query processing and debouncing
- Voter selection and state management
- Vote marking with success/error scenarios
- Performance testing for large datasets
- Arabic text handling and normalization

**File**: `tests/gui/test_voter_search_ui.py`

**GUI Test Scenarios**:
```python
@pytest.mark.qt
def test_search_interaction(qtbot, voter_search_window):
    """Test search input and result display"""
    # Type in search box
    # Verify results update
    # Click on voter card
    # Verify selection updates

@pytest.mark.qt
def test_vote_marking(qtbot, voter_search_window, mock_dao):
    """Test vote button interaction"""
    # Select unvoted voter
    # Click vote button
    # Verify DAO call
    # Verify UI update
    # Verify snackbar display
```

### Step 10: Internationalization Setup

**File**: `src/JCSELECT/i18n/ar_LB.ts`

**Translation Strings**:
```xml
<message>
    <source>Search voters...</source>
    <translation>البحث عن الناخبين...</translation>
</message>
<message>
    <source>Mark as voted</source>
    <translation>تم</translation>
</message>
<message>
    <source>Vote recorded successfully</source>
    <translation>تمت عملية التصويت بنجاح</translation>
</message>
```

**QML Integration**:
- Wrap all user-visible strings with `qsTr()`
- Configure Qt translation loading in main.py
- Add language switching capability (future)

### Step 11: Error Handling & User Feedback

**Error Scenarios**:
- Database connection failures
- Search query timeouts
- Vote marking conflicts (voter already voted)
- Invalid voter data
- Network issues (future sync scenarios)

**User Feedback Mechanisms**:
- Loading indicators during operations
- Error messages in snackbars
- Success confirmations with animations
- Progress indicators for long operations
- Graceful degradation for offline scenarios

### Step 12: Performance Monitoring

**Metrics to Track**:
- Search query execution time
- UI rendering performance
- Memory usage with large datasets
- Database connection pool usage
- User interaction response times

**Implementation**:
- Add performance logging in controller
- Monitor search execution times
- Track UI frame rates during animations
- Log database query performance
- Add debug mode for performance metrics

## 5. Execution Steps

```bash
# 1. Extend theme system
# Edit src/JCSELECT/ui/Theme.qml (add Material 3 tokens)

# 2. Create component directory structure
mkdir -p src/JCSELECT/ui/components

# 3. Implement reusable components
# - src/JCSELECT/ui/components/SearchBar.qml
# - src/JCSELECT/ui/components/VoterCard.qml
# - src/JCSELECT/ui/components/VoterDetailPane.qml
# - src/JCSELECT/ui/components/VoteButton.qml
# - src/JCSELECT/ui/components/Snackbar.qml
# - src/JCSELECT/ui/components/qmldir

# 4. Create data transfer objects
# - src/JCSELECT/models/dto.py

# 5. Implement voter search controller
# - src/JCSELECT/controllers/voter_search_controller.py

# 6. Create main voter search window
# - src/JCSELECT/ui/VoterSearchWindow.qml

# 7. Update main application
# Edit src/JCSELECT/ui/App.qml (integrate VoterSearchWindow)

# 8. Add database indexes
# Create Alembic migration for search optimization

# 9. Implement tests
# - tests/unit/test_voter_search_controller.py
# - tests/gui/test_voter_search_ui.py

# 10. Add translation strings
# - src/JCSELECT/i18n/ar_LB.ts

# 11. Update main.py for translation loading
# Edit src/JCSELECT/main.py

# 12. Run tests and validate
poetry run pytest tests/gui/test_voter_search_ui.py -v
poetry run python -m JCSELECT

# 13. Performance testing
# Test with seeded demo data (100 voters)
# Measure search response times
# Validate UI responsiveness
```

## 6. Acceptance Criteria

- ✅ Running `python -m JCSELECT` opens Voter Search screen with proper Arabic RTL layout
- ✅ Typing part of a voter name or number filters results instantly (< 100ms for 100 voters)
- ✅ Search supports both Arabic and English text input
- ✅ Clicking on a voter card displays detailed information in the detail pane
- ✅ Clicking "تم" button successfully marks voter as voted and updates the database
- ✅ Vote marking updates the UI immediately without requiring page refresh
- ✅ Snackbar notification "تمت عملية التصويت بنجاح" appears for 2 seconds after successful vote
- ✅ Already-voted voters display with green checkmark and disabled vote button
- ✅ Ctrl+F keyboard shortcut focuses the search input
- ✅ Error scenarios display appropriate user-friendly messages
- ✅ `pytest` passes with new GUI tests enabled and running headless
- ✅ All components follow Material 3 design principles
- ✅ UI remains responsive during search operations
- ✅ Arabic text displays correctly with proper RTL alignment

## 7. Future Enhancements

- **Advanced Search**: Filters by voting status, age groups, gender
- **Bulk Operations**: Mark multiple voters as voted
- **Voter Photos**: Display voter photographs for verification
- **Print Functionality**: Print voter lists and reports
- **Accessibility**: Screen reader support and keyboard navigation
- **Mobile Layout**: Responsive design for tablet use

This specification provides a comprehensive foundation for building a professional, user-friendly voter search and check-in interface that meets the needs of Lebanese election operations.
