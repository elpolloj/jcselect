import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import jcselect.ui.components 1.0
import "../"

Rectangle {
    id: root
    
    property alias isLoading: resultsTable.isLoading
    
    signal sortRequested(string columnKey, bool descending)
    
    color: Theme.backgroundColor
    
    readonly property var columns: [
        {
            "key": "candidate_name",
            "title": qsTr("اسم المرشح"),
            "type": "text",
            "align": "right",
            "width": 200,
            "sortable": true
        },
        {
            "key": "party_name",
            "title": qsTr("الحزب"),
            "type": "text",
            "align": "right",
            "width": 150,
            "sortable": true
        },
        {
            "key": "total_votes",
            "title": qsTr("إجمالي الأصوات"),
            "type": "number",
            "align": "center",
            "width": 120,
            "sortable": true
        },
        {
            "key": "rank",
            "title": qsTr("الترتيب"),
            "type": "number",
            "align": "center",
            "width": 80,
            "sortable": false
        }
    ]
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing
        spacing: Theme.spacingMedium
        
        // Page header
        Text {
            text: qsTr("نتائج المرشحين")
            font.pixelSize: Theme.titleLarge
            font.weight: Font.Bold
            color: Theme.textColor
            Layout.fillWidth: true
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
        
        // Search bar for candidate filtering
        TextField {
            id: searchField
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.buttonHeight
            
            placeholderText: qsTr("البحث عن مرشح...")
            
            background: Rectangle {
                color: Theme.backgroundColor
                border.color: searchField.activeFocus ? Theme.primaryColor : "#e0e0e0"
                border.width: searchField.activeFocus ? 2 : 1
                radius: Theme.radius
            }
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
            
            // Connect to controller filter method
            onTextChanged: {
                if (typeof resultsController !== 'undefined' && resultsController.setCandidateFilter) {
                    resultsController.setCandidateFilter(text)
                }
            }
        }
        
        // Results table
        ResultsTable {
            id: resultsTable
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            columns: root.columns
            model: resultsController.candidateTotals
            isLoading: resultsController.isSyncing
            currentSortColumn: "total_votes"
            sortDescending: true
            
            onSortRequested: function(columnKey, descending) {
                root.sortRequested(columnKey, descending)
            }
        }
    }
    
    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
} 