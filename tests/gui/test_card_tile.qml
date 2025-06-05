import QtQuick 2.15
import QtQuick.Controls 2.15
import QtTest 1.15
import jcselect.components 1.0

TestCase {
    id: testCase
    name: "CardTileTests"
    width: 400
    height: 300

    Component {
        id: cardTileComponent
        CardTile {
            id: cardTile
        }
    }

    function test_cardTileInstantiation() {
        // Test that CardTile can be created without errors
        var cardTile = createTemporaryObject(cardTileComponent, testCase)
        verify(cardTile !== null, "CardTile should be created successfully")
    }

    function test_cardTileProperties() {
        // Test that properties can be set and retrieved
        var cardTile = createTemporaryObject(cardTileComponent, testCase)
        
        // Set properties
        cardTile.title = "Test Title"
        cardTile.subtitle = "Test Subtitle"
        cardTile.iconSource = "qrc:/icons/test.svg"
        cardTile.badgeText = "5"
        cardTile.badgeVisible = true
        cardTile.enabled = true
        
        // Verify properties
        compare(cardTile.title, "Test Title", "Title should be set correctly")
        compare(cardTile.subtitle, "Test Subtitle", "Subtitle should be set correctly")
        compare(cardTile.iconSource, "qrc:/icons/test.svg", "Icon source should be set correctly")
        compare(cardTile.badgeText, "5", "Badge text should be set correctly")
        compare(cardTile.badgeVisible, true, "Badge visibility should be set correctly")
        compare(cardTile.enabled, true, "Enabled state should be set correctly")
    }

    function test_cardTileSignals() {
        // Test that signals can be connected
        var cardTile = createTemporaryObject(cardTileComponent, testCase)
        
        var clickedSignalSpy = signalSpy.createObject(testCase, {
            target: cardTile,
            signalName: "clicked"
        })
        
        var rightClickedSignalSpy = signalSpy.createObject(testCase, {
            target: cardTile,
            signalName: "rightClicked"
        })
        
        verify(clickedSignalSpy.valid, "clicked signal should be valid")
        verify(rightClickedSignalSpy.valid, "rightClicked signal should be valid")
    }

    function test_cardTileDefaultValues() {
        // Test default property values
        var cardTile = createTemporaryObject(cardTileComponent, testCase)
        
        compare(cardTile.title, "", "Default title should be empty")
        compare(cardTile.subtitle, "", "Default subtitle should be empty")
        compare(cardTile.iconSource, "", "Default iconSource should be empty")
        compare(cardTile.badgeText, "", "Default badgeText should be empty")
        compare(cardTile.badgeVisible, false, "Default badgeVisible should be false")
        compare(cardTile.enabled, true, "Default enabled should be true")
        compare(cardTile.width, 200, "Default width should be 200")
        compare(cardTile.height, 160, "Default height should be 160")
    }

    Component {
        id: signalSpy
        SignalSpy {}
    }
} 