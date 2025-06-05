pragma Singleton
import QtQuick 2.15

QtObject {
    // Dark mode detection with fallback
    readonly property bool isDarkMode: {
        try {
            return Qt.application.palette && Qt.application.palette.window 
                ? Qt.application.palette.window.hslLightness < 0.4
                : false
        } catch (e) {
            return false  // Fallback to light mode if palette is unavailable
        }
    }
    
    // Cairo Font Integration (with fallbacks)
    readonly property string primaryFont: {
        var availableFonts = Qt.fontFamilies()
        if (availableFonts.includes("Cairo")) {
            return "Cairo"
        } else if (availableFonts.includes("Noto Sans Arabic")) {
            return "Noto Sans Arabic"
        } else {
            return "Segoe UI"
        }
    }
    
    // Material 3 Color System - Primary
    readonly property color primary: "#1976D2"
    readonly property color primaryText: "#FFFFFF"
    readonly property color primaryContainer: "#E3F2FD"
    readonly property color primaryContainerText: "#0D47A1"
    
    // Material 3 Color System - Surface & Background
    readonly property color surface: "#FFFFFF"
    readonly property color surfaceVariant: "#F8F9FA"
    readonly property color surfaceText: "#1C1B1F"
    readonly property color surfaceVariantText: "#49454F"
    readonly property color background: "#FEFBFF"
    readonly property color backgroundText: "#1C1B1F"
    
    // Enhanced Surface Variants (from spec)
    readonly property color surfaceContainerLow: "#f7f7fa"
    readonly property color surfaceContainerHigh: "#eeeef1"
    
    // Gradient colors for header (from spec)
    readonly property color headerGradientStart: "#ff0000"
    readonly property color headerGradientEnd: "#d40000"
    
    // Shadow colors (from spec)
    readonly property color shadowLight: "#00000015"
    readonly property color shadowMedium: "#00000025"
    
    // Material 3 Color System - Semantic Colors
    readonly property color success: "#4CAF50"
    readonly property color successText: "#FFFFFF"
    readonly property color successContainer: "#D1FFCA"
    readonly property color successContainerText: "#2E7D32"
    
    readonly property color warning: "#FF9800"
    readonly property color warningText: "#FFFFFF"
    readonly property color warningContainer: "#FFF3C4"
    readonly property color warningContainerText: "#E65100"
    
    readonly property color error: "#F44336"
    readonly property color errorText: "#FFFFFF"
    readonly property color errorContainer: "#FFEBEE"
    readonly property color errorContainerText: "#C62828"
    
    // Status colors (from spec)
    readonly property color successContent: "#155724"
    readonly property color stableIndicator: "#28a745"
    
    // Material 3 Elevation Shadows
    readonly property color elevation1: "#E0E0E0"
    readonly property color elevation3: "#BDBDBD"
    readonly property color elevation6: "#9E9E9E"
    
    // Badge System
    readonly property color badgeBackground: "#E8F5E8"
    readonly property color badgeText: "#2E7D32"
    readonly property color badgeError: "#FFEBEE"
    readonly property color badgeErrorText: "#C62828"
    
    // Legacy Color Compatibility
    readonly property color primaryColor: primary
    readonly property color primaryContainerColor: primaryContainer
    readonly property color primaryContainerOn: primaryContainerText
    readonly property color secondaryContainer: surfaceVariant
    readonly property color errorContainerColor: errorContainer
    readonly property color successContainerColor: successContainer
    readonly property color backgroundColor: background
    readonly property color surfaceColor: surface
    readonly property color textColor: surfaceText
    readonly property color successColor: success
    readonly property color errorColor: error
    readonly property color warningColor: warning
    readonly property color outlineColor: "#79747E"
    
    // Additional legacy compatibility for "on*" names
    readonly property color onPrimary: primaryText
    readonly property color onSurface: surfaceText
    readonly property color onBackground: backgroundText
    readonly property color onSuccess: successText
    readonly property color onError: errorText
    readonly property color onWarning: warningText
    readonly property color onPrimaryContainer: primaryContainerText
    readonly property color onSurfaceVariant: surfaceVariantText
    readonly property color onSuccessContainer: successContainerText
    readonly property color onWarningContainer: warningContainerText
    readonly property color onErrorContainer: errorContainerText
    
    // Material 3 Typography Scale (font objects) - Updated with Cairo font
    readonly property font displayLargeFont: Qt.font({family: primaryFont, pointSize: 36, weight: Font.Medium})
    readonly property font displayMediumFont: Qt.font({family: primaryFont, pointSize: 28, weight: Font.Medium})
    readonly property font headlineLargeFont: Qt.font({family: primaryFont, pointSize: 24, weight: Font.Medium})
    readonly property font headlineMediumFont: Qt.font({family: primaryFont, pointSize: 18, weight: Font.Medium})
    readonly property font titleLargeFont: Qt.font({family: primaryFont, pointSize: 16, weight: Font.Medium})
    readonly property font titleMediumFont: Qt.font({family: primaryFont, pointSize: 14, weight: Font.Medium})
    readonly property font titleSmallFont: Qt.font({family: primaryFont, pointSize: 12, weight: Font.Medium})
    readonly property font bodyLargeFont: Qt.font({family: primaryFont, pointSize: 14, weight: Font.Normal})
    readonly property font bodyMediumFont: Qt.font({family: primaryFont, pointSize: 12, weight: Font.Normal})
    readonly property font bodySmallFont: Qt.font({family: primaryFont, pointSize: 11, weight: Font.Normal})
    readonly property font labelLargeFont: Qt.font({family: primaryFont, pointSize: 11, weight: Font.Bold})
    readonly property font labelMediumFont: Qt.font({family: primaryFont, pointSize: 10, weight: Font.Bold})
    readonly property font labelSmallFont: Qt.font({family: primaryFont, pointSize: 9, weight: Font.Bold})
    
    // Additional typography from spec
    readonly property font displayLarge: Qt.font({family: primaryFont, pixelSize: 48, weight: Font.Bold})
    readonly property font headlineSmall: Qt.font({family: primaryFont, pixelSize: 24, weight: Font.DemiBold})
    readonly property font titleMedium: Qt.font({family: primaryFont, pixelSize: 16, weight: Font.Medium})
    
    // Legacy Typography Compatibility (using pixel sizes for old code that expects integers)
    readonly property int displayLargeSize: 36
    readonly property int displayMediumSize: 28
    readonly property int headlineLarge: 24  
    readonly property int headlineMedium: 18
    readonly property int titleLarge: 16
    readonly property int titleMediumSize: 14
    readonly property int titleSmall: 12
    readonly property int bodyLarge: 14
    readonly property int bodyMedium: 12
    readonly property int bodySmall: 11
    readonly property int labelLarge: 11
    readonly property int labelMediumSize: 10
    readonly property int labelSmall: 9
    // Additional legacy sizes that don't conflict
    readonly property int headlineSize: 32
    readonly property int titleSize: 20
    readonly property int bodySize: 14
    readonly property int captionSize: 12
    
    // Material 3 Animation System
    readonly property int durationFast: 150
    readonly property int durationMedium: 250
    readonly property int durationSlow: 400
    readonly property var easingStandard: Easing.OutCubic
    readonly property var easingEmphasized: Easing.OutQuint
    
    // Animation durations from spec
    readonly property int valueChangeDuration: 300
    readonly property int hoverDuration: 150
    readonly property int pulseDuration: 1500
    
    // Legacy Animation Compatibility
    readonly property int animationDurationShort: durationFast
    readonly property int animationDurationMedium: durationMedium
    readonly property int animationDurationLong: durationSlow
    readonly property real animationEasingStandard: easingStandard
    readonly property real animationEasingEmphasized: easingEmphasized
    
    // Component Sizing
    readonly property int searchBarHeight: 56
    readonly property int cardMinHeight: 72
    readonly property int buttonHeight: 40
    readonly property int snackbarHeight: 48
    
    // Material 3 Spacing System
    readonly property int spacing: 16
    readonly property int margin: 24
    readonly property int radius: 8
    readonly property int spacingTiny: 4
    readonly property int spacingSmall: 8
    readonly property int spacingMedium: 16
    readonly property int spacingLarge: 24
    readonly property int spacingXLarge: 32
    
    // Shape System
    readonly property int cornerRadius: 12
    readonly property int cornerRadiusSmall: 8
    readonly property int cornerRadiusLarge: 16
    
    // Icon Resource Resolution
    function iconPath(iconName) {
        // For development, use direct file paths
        var basePath = "file:///C:/Users/USER/Desktop/jcselect/resources/icons/"
        return basePath + iconName
    }
    
    function legacyIconPath(iconName) {
        // Use direct file paths for reliable icon loading
        var basePath = "file:///C:/Users/USER/Desktop/jcselect/resources/icons/"
        return basePath + iconName
    }
    
    // RTL-aware margin and padding helpers
    function leftMargin(isRTL) {
        return isRTL ? 0 : margin
    }
    
    function rightMargin(isRTL) {
        return isRTL ? margin : 0
    }
    
    function startPadding(isRTL) {
        return isRTL ? spacing : 0
    }
    
    function endPadding(isRTL) {
        return isRTL ? 0 : spacing
    }
} 