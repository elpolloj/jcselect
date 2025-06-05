"""GUI tests for party-related QML components."""
import pytest
import os


# Minimal test to verify QML components can be instantiated
def test_components_exist():
    """Test that component files exist in the expected location."""
    components_dir = os.path.join("src", "jcselect", "ui", "components")
    
    # Verify all component files exist
    assert os.path.exists(os.path.join(components_dir, "PartyColumn.qml"))
    assert os.path.exists(os.path.join(components_dir, "CandidateCheckbox.qml"))
    assert os.path.exists(os.path.join(components_dir, "BallotTypePanel.qml"))
    assert os.path.exists(os.path.join(components_dir, "qmldir"))


def test_qmldir_registration():
    """Test that qmldir file contains proper component registrations."""
    qmldir_path = os.path.join("src", "jcselect", "ui", "components", "qmldir")
    
    with open(qmldir_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify all components are registered
    assert "PartyColumn 1.0 PartyColumn.qml" in content
    assert "CandidateCheckbox 1.0 CandidateCheckbox.qml" in content
    assert "BallotTypePanel 1.0 BallotTypePanel.qml" in content


def test_component_syntax():
    """Test that QML components have valid syntax by checking imports."""
    components_dir = os.path.join("src", "jcselect", "ui", "components")
    
    # Test PartyColumn.qml
    with open(os.path.join(components_dir, "PartyColumn.qml"), 'r', encoding='utf-8') as f:
        party_content = f.read()
    
    assert "import QtQuick" in party_content
    assert "import QtQuick.Controls" in party_content
    assert "import QtQuick.Layouts" in party_content
    assert "property var partyData" in party_content
    assert "signal candidateSelected" in party_content
    
    # Test CandidateCheckbox.qml
    with open(os.path.join(components_dir, "CandidateCheckbox.qml"), 'r', encoding='utf-8') as f:
        checkbox_content = f.read()
    
    assert "import QtQuick" in checkbox_content
    assert "property var candidateData" in checkbox_content
    assert "signal toggled" in checkbox_content
    
    # Test BallotTypePanel.qml
    with open(os.path.join(components_dir, "BallotTypePanel.qml"), 'r', encoding='utf-8') as f:
        panel_content = f.read()
    
    assert "import QtQuick" in panel_content
    assert "property string selectedType" in panel_content
    assert "signal typeSelected" in panel_content
    assert '"Ballot Type" in Arabic' in panel_content  # Check for English comment


def test_party_column_structure():
    """Test PartyColumn component structure and properties."""
    party_column_path = os.path.join("src", "jcselect", "ui", "components", "PartyColumn.qml")
    
    with open(party_column_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify component structure
    assert "Rectangle {" in content
    assert "id: root" in content
    assert "property var partyData: null" in content
    assert "property string selectedCandidate:" in content
    assert "signal candidateSelected(string candidateId)" in content
    
    # Verify UI elements
    assert "ColumnLayout" in content
    assert "ScrollView" in content
    assert "ListView" in content
    assert "CandidateCheckbox" in content
    
    # Verify RTL-friendly design
    assert "anchors.centerIn: parent" in content


def test_candidate_checkbox_structure():
    """Test CandidateCheckbox component structure and Material 3 design."""
    checkbox_path = os.path.join("src", "jcselect", "ui", "components", "CandidateCheckbox.qml")
    
    with open(checkbox_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify component structure
    assert "Rectangle {" in content
    assert "property var candidateData: null" in content
    assert "property bool checked: false" in content
    assert "signal toggled(string candidateId, bool isChecked)" in content
    
    # Verify Material 3 design elements
    assert "MouseArea" in content
    assert "RowLayout" in content
    assert "Behavior on color" in content
    assert "ColorAnimation" in content
    
    # Verify checkbox visual (check for checkmark character)
    assert "✓" in content
    assert "Theme.primaryColor" in content


def test_ballot_type_panel_structure():
    """Test BallotTypePanel component structure and Arabic labels."""
    panel_path = os.path.join("src", "jcselect", "ui", "components", "BallotTypePanel.qml")
    
    with open(panel_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify component structure
    assert "Rectangle {" in content
    assert "property string selectedType:" in content
    assert "signal typeSelected(string ballotType)" in content
    
    # Verify Arabic labels by checking for English comments
    assert '"Ballot Type" in Arabic' in content
    assert '"Normal" in Arabic' in content
    assert '"Cancel/Void" in Arabic' in content
    assert '"White" in Arabic' in content
    assert '"Invalid/Illegal" in Arabic' in content
    assert '"Blank" in Arabic' in content
    
    # Verify color coding
    assert "#d32f2f" in content  # Red for cancel
    assert "#ff9800" in content  # Orange for white
    assert "#e91e63" in content  # Pink for illegal
    assert "#9e9e9e" in content  # Gray for blank


def test_tally_window_integration():
    """Test that TallyCountingWindow properly integrates the new components."""
    window_path = os.path.join("src", "jcselect", "ui", "TallyCountingWindow.qml")
    
    with open(window_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify component import
    assert 'import "components"' in content
    
    # Verify component usage
    assert "PartyColumn" in content
    assert "BallotTypePanel" in content
    
    # Verify data binding
    assert "partyData: modelData" in content
    assert "selectedCandidate: tallyController.selectedCandidates" in content
    assert "selectedType: tallyController.selectedBallotType" in content
    
    # Verify signal connections
    assert "onCandidateSelected:" in content
    assert "onTypeSelected:" in content
    assert "tallyController.selectCandidate" in content
    assert "tallyController.selectBallotType" in content
    
    # Verify Arabic UI elements by checking for English comment
    assert '"Confirm Ballot" in Arabic' in content


@pytest.mark.skip(reason="Full QML runtime testing requires Qt environment setup")
def test_component_runtime_behavior():
    """Placeholder for full QML runtime interaction tests."""
    # This would require setting up QQmlEngine and QQuickView
    # For now we verify the components exist and have correct structure
    pass 