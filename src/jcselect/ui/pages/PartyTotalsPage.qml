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
            "key": "party_name",
            "title": qsTr("الحزب"),
            "type": "text",
            "align": "right",
            "width": 200,
            "sortable": true,
            "alignment": Qt.AlignRight
        },
        {
            "key": "total_votes",
            "title": qsTr("الأصوات"),
            "type": "number",
            "align": "center",
            "width": 120,
            "sortable": true,
            "alignment": Qt.AlignHCenter,
            "numeric": true
        },
        {
            "key": "percentage",
            "title": qsTr("النسبة ٪"),
            "type": "percentage",
            "align": "center",
            "width": 120,
            "sortable": true,
            "alignment": Qt.AlignHCenter,
            "numeric": true
        }
    ]
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing
        spacing: Theme.spacingMedium
        
        // Page header
        Text {
            text: qsTr("إجمالي أصوات الأحزاب")
            font.pixelSize: Theme.titleLarge
            font.weight: Font.Bold
            color: Theme.textColor
            Layout.fillWidth: true
            
            LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        }
        
        // Results table
        ResultsTable {
            id: resultsTable
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            columns: root.columns
            model: resultsController.partyTotals
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