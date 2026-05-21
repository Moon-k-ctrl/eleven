import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    height: 36
    color: "#1A7CE0C3" // accentMint at 10%
    radius: Theme.radiusSM
    visible: bridge.multiSelectMode

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingSM
        anchors.rightMargin: Theme.spacingSM
        spacing: Theme.spacingSM

        Text {
            text: "已选 " + bridge.selectedCount + " 项"
            font.pixelSize: Theme.fontSizeSM
            font.family: Theme.fontFamilyPrimary
            color: Theme.accentMint
        }

        Item { Layout.fillWidth: true }

        // Select all
        Rectangle {
            Layout.preferredWidth: selectAllText.implicitWidth + Theme.spacingMD * 2
            Layout.preferredHeight: 24
            radius: Theme.radiusSM
            color: selectAllMouse.containsMouse ? Theme.bgHover : "transparent"

            Text {
                id: selectAllText
                anchors.centerIn: parent
                text: "全选"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilyPrimary
                color: Theme.textSecondary
            }

            MouseArea {
                id: selectAllMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: bridge.selectAll()
            }
        }

        // Export
        Rectangle {
            Layout.preferredWidth: exportText.implicitWidth + Theme.spacingMD * 2
            Layout.preferredHeight: 24
            radius: Theme.radiusSM
            color: exportMouse.containsMouse ? Theme.bgHover : "transparent"

            Text {
                id: exportText
                anchors.centerIn: parent
                text: "导出"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilyPrimary
                color: Theme.accentCyan
            }

            MouseArea {
                id: exportMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: bridge.exportRequested()
            }
        }

        // Delete
        Rectangle {
            Layout.preferredWidth: deleteText.implicitWidth + Theme.spacingMD * 2
            Layout.preferredHeight: 24
            radius: Theme.radiusSM
            color: deleteMouse.containsMouse ? "#1AF06464" : "transparent"

            Text {
                id: deleteText
                anchors.centerIn: parent
                text: "删除"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilyPrimary
                color: Theme.error
            }

            MouseArea {
                id: deleteMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    var ids = bridge.getSelectedItemIds()
                    if (ids.length > 0) bridge.batchDelete(ids)
                    bridge.cancelMultiSelect()
                }
            }
        }

        // Cancel
        Rectangle {
            Layout.preferredWidth: cancelText.implicitWidth + Theme.spacingMD * 2
            Layout.preferredHeight: 24
            radius: Theme.radiusSM
            color: cancelMouse.containsMouse ? Theme.bgHover : "transparent"

            Text {
                id: cancelText
                anchors.centerIn: parent
                text: "取消"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilyPrimary
                color: Theme.textSecondary
            }

            MouseArea {
                id: cancelMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: bridge.cancelMultiSelect()
            }
        }
    }
}
