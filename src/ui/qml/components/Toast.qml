import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    width: toastText.implicitWidth + spacing * 2 + (undoBtn.visible ? undoBtn.width + spacing : 0)
    height: 32
    radius: Theme.radiusSM
    color: bgColor
    opacity: 0
    visible: opacity > 0

    property string message: ""
    property string type: "info"  // "info" | "success" | "warning" | "error"
    property bool showUndo: false
    property int duration: 2500
    property int spacing: Theme.spacingSM

    signal dismissed()
    signal undoClicked()

    // Colors based on type
    readonly property color bgColor: {
        switch (type) {
            case "success": return "#1a3a2e"
            case "warning": return "#3a2a1a"
            case "error": return "#3a1a1a"
            default: return "#1a2a3a"
        }
    }
    readonly property color textColor: {
        switch (type) {
            case "success": return Theme.accentMint
            case "warning": return Theme.accentGold
            case "error": return Theme.error
            default: return Theme.accentCyan
        }
    }
    readonly property color borderColor: {
        switch (type) {
            case "success": return Qt.rgba(0.49, 0.88, 0.76, 0.3)
            case "warning": return Qt.rgba(0.95, 0.72, 0.29, 0.3)
            case "error": return Qt.rgba(0.94, 0.39, 0.39, 0.3)
            default: return Qt.rgba(0.4, 0.72, 0.78, 0.3)
        }
    }

    border.color: borderColor
    border.width: 1

    // Icon
    readonly property string icon: {
        switch (type) {
            case "success": return "✓"
            case "warning": return "⚠"
            case "error": return "✕"
            default: return "ℹ"
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: root.spacing
        anchors.rightMargin: root.spacing
        spacing: root.spacing

        Text {
            text: root.icon + " " + root.message
            font.pixelSize: Theme.fontSizeXS
            font.family: Theme.fontFamilyPrimary
            color: root.textColor
            Layout.fillWidth: true
        }

        // Undo button
        Rectangle {
            id: undoBtn
            visible: root.showUndo
            Layout.preferredWidth: undoText.implicitWidth + 12
            Layout.preferredHeight: 22
            radius: Theme.radiusSM
            color: undoMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.1) : "transparent"
            border.color: root.textColor
            border.width: 1

            Text {
                id: undoText
                anchors.centerIn: parent
                text: "撤销"
                font.pixelSize: 10
                font.weight: Theme.fontBold
                font.family: Theme.fontFamilyPrimary
                color: root.textColor
            }

            MouseArea {
                id: undoMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.undoClicked()
                    hideTimer.stop()
                    root.opacity = 0
                }
            }
        }
    }

    // Auto-hide timer
    Timer {
        id: hideTimer
        interval: root.duration
        onTriggered: {
            fadeOut.start()
        }
    }

    // Animations
    NumberAnimation {
        id: fadeIn
        target: root
        property: "opacity"
        from: 0; to: 1
        duration: 150
        easing.type: Easing.OutCubic
    }

    NumberAnimation {
        id: fadeOut
        target: root
        property: "opacity"
        from: 1; to: 0
        duration: 200
        easing.type: Easing.InCubic
        onFinished: root.dismissed()
    }

    // Public API
    function show(msg, toastType, undo, dur) {
        message = msg || ""
        type = toastType || "info"
        showUndo = undo || false
        duration = dur || 2500
        fadeIn.start()
        hideTimer.restart()
    }

    function hide() {
        hideTimer.stop()
        fadeOut.start()
    }
}
