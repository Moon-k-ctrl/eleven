import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: titleBar
    implicitHeight: headerRow.height + toolbarRow.height
    color: "transparent"

    // Status color mapping
    function statusColor() {
        switch (bridge.status) {
            case "online": return Theme.statusOnline
            case "warning": return Theme.statusWarning
            case "error": return Theme.statusError
            default: return Theme.statusOffline
        }
    }

    // ── Header: status + title + capacity + window controls ──
    Rectangle {
        id: headerRow
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 50
        color: Theme.bgPanelHeader

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacingMD
            anchors.rightMargin: Theme.spacingMD
            spacing: 7

            // Status dot
            Rectangle {
                width: 8
                height: 8
                radius: 4
                color: statusColor()
            }

            // Title — draggable
            Text {
                text: "拾遗"
                font.pixelSize: Theme.fontSizeLG
                font.weight: Theme.fontBold
                font.family: Theme.fontFamilyPrimary
                color: Theme.textPrimary

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -8
                    onPressed: function(mouse) {
                        titleBar.Window.window.startSystemMove()
                    }
                }
            }

            // Capacity label
            Text {
                text: "(" + bridge.count + "/" + bridge.maxItems + ")"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilySecondary
                font.weight: Theme.fontMedium
                color: "#6E8A9A"
            }

            Item { Layout.fillWidth: true }

            // Theme toggle button
            Rectangle {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                color: "transparent"

                Text {
                    anchors.centerIn: parent
                    text: Theme.isDark ? "☀" : "🌙"
                    font.pixelSize: 12
                    color: themeToggleMouse.containsMouse ? Theme.textPrimary : "#8FB2C2"
                }

                MouseArea {
                    id: themeToggleMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bridge.toggleTheme()
                }
            }

            // Minimize button
            Rectangle {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                color: "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "−"
                    font.pixelSize: 16
                    font.family: Theme.fontFamilySecondary
                    color: minimizeMouse.containsMouse ? Theme.textPrimary : "#8FB2C2"
                }

                MouseArea {
                    id: minimizeMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: titleBar.Window.window.showMinimized()
                }
            }

            // Close button
            Rectangle {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                color: "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "×"
                    font.pixelSize: 16
                    font.family: Theme.fontFamilySecondary
                    color: closeMouse.containsMouse ? Theme.textPrimary : "#8FB2C2"
                }

                MouseArea {
                    id: closeMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: titleBar.Window.window.visible = false
                }
            }
        }

        // Bottom border
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.lineSoft
        }
    }

    // ── Toolbar: action buttons ──
    Rectangle {
        id: toolbarRow
        anchors.top: headerRow.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 42
        color: Theme.bgPanelHeader

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacingMD
            anchors.rightMargin: Theme.spacingMD
            anchors.topMargin: 5
            anchors.bottomMargin: 5
            spacing: 8

            // Merge button (visible when multi-select)
            ShiyiButton {
                Layout.fillWidth: true
                Layout.minimumWidth: 58
                text: "合并"
                iconText: "⧉"
                visible: bridge.multiSelectMode
                onClicked: {
                    var ids = bridge.getSelectedItemIds()
                    if (ids.length > 1) bridge.mergeItems(ids)
                }
            }

            ShiyiButton {
                Layout.fillWidth: true
                Layout.minimumWidth: 58
                text: "预览栏"
                iconText: "◨"
                primary: true
                onClicked: bridge.previewBarToggle()
            }

            ShiyiButton {
                Layout.fillWidth: true
                Layout.minimumWidth: 58
                text: "导出"
                iconText: "⇣"
                onClicked: bridge.exportRequested()
            }

            ShiyiButton {
                Layout.fillWidth: true
                Layout.minimumWidth: 58
                text: "短语"
                iconText: "⚡"
                onClicked: bridge.togglePhrasesPanel()
            }

            ShiyiButton {
                Layout.fillWidth: true
                Layout.minimumWidth: 58
                text: "回收站"
                iconText: "🗑"
                onClicked: bridge.showTrash()
            }

            ShiyiButton {
                Layout.fillWidth: true
                Layout.minimumWidth: 58
                text: "备份"
                iconText: "💾"
                onClicked: backupMenu.popup()
            }

            ShiyiButton {
                Layout.fillWidth: true
                Layout.minimumWidth: 58
                text: "清空"
                iconText: "×"
                danger: true
                onClicked: bridge.clearAll()
            }
        }
    }

    // Backup/Restore menu
    Menu {
        id: backupMenu

        MenuItem {
            text: "💾 导出备份 (JSON)"
            onTriggered: bridge.exportBackup()
        }
        MenuItem {
            text: "📂 导入备份 (JSON)"
            onTriggered: bridge.importRestore()
        }
    }
}
