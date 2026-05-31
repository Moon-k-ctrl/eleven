import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    height: expanded ? headerRow.height + gridContainer.height + footerRow.height : headerRow.height
    color: "#0AFFFFFF"
    radius: Theme.radiusSM
    border.color: Theme.lineSoft
    border.width: 1

    property bool expanded: true

    Behavior on height {
        NumberAnimation { duration: Theme.animNormal; easing.type: Easing.InOutQuad }
    }

    // ── Header ──
    RowLayout {
        id: headerRow
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Theme.spacingSM
        height: 28

        Text {
            text: "暂存架"
            font.pixelSize: Theme.fontSizeSM
            font.weight: Theme.fontBold
            font.family: Theme.fontFamilyPrimary
            color: Theme.textSecondary
        }

        Text {
            text: stagingModel.count + "/20"
            font.pixelSize: Theme.fontSizeXS
            font.family: Theme.fontFamilySecondary
            color: Theme.textPlaceholder
        }

        Item { Layout.fillWidth: true }

        // Collapse/expand toggle
        Rectangle {
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            color: collapseMouse.containsMouse ? Theme.bgHover : "transparent"
            radius: Theme.radiusSM

            Text {
                anchors.centerIn: parent
                text: root.expanded ? "▾" : "▸"
                font.pixelSize: Theme.fontSizeXS
                color: Theme.textTertiary
            }

            MouseArea {
                id: collapseMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.expanded = !root.expanded
            }
        }

        // Clear all button
        Rectangle {
            visible: stagingModel.count > 0
            Layout.preferredWidth: clearText.implicitWidth + Theme.spacingSM * 2
            Layout.preferredHeight: 20
            color: clearMouse.containsMouse ? "#1AF06464" : "transparent"
            radius: Theme.radiusSM

            Text {
                id: clearText
                anchors.centerIn: parent
                text: "清空"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilyPrimary
                color: clearMouse.containsMouse ? Theme.error : Theme.textTertiary
            }

            MouseArea {
                id: clearMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: bridge.clearStaging()
            }
        }
    }

    // ── Grid container ──
    Item {
        id: gridContainer
        anchors.top: headerRow.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.spacingSM
        anchors.rightMargin: Theme.spacingSM
        height: stagingModel.count > 0 ? grid.contentHeight : emptyHint.height + Theme.spacingSM

        // Empty hint
        Column {
            id: emptyHint
            visible: stagingModel.count === 0
            anchors.centerIn: parent
            spacing: 4

            Text {
                text: "📥"
                font.pixelSize: 24
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                text: "右键历史项 → 发送到暂存架"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilyPrimary
                color: Theme.textPlaceholder
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }

        // Grid view
        GridView {
            id: grid
            anchors.fill: parent
            visible: stagingModel.count > 0
            model: stagingModel
            cellWidth: 96 + Theme.spacingXS
            cellHeight: 96 + Theme.spacingXS
            clip: true
            interactive: false

            delegate: StagingCardDelegate {}
        }
    }

    // ── Footer ──
    RowLayout {
        id: footerRow
        anchors.top: gridContainer.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.spacingSM
        anchors.rightMargin: Theme.spacingSM
        height: stagingModel.count > 0 ? 20 : 0
        visible: stagingModel.count > 0

        Item { Layout.fillWidth: true }
    }

    // Bottom separator
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.lineSoft
    }
}
