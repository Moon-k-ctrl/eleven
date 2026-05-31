import QtQuick 2.15
import QtQuick.Layouts 1.15

RowLayout {
    id: root
    spacing: Theme.spacingXS

    property string currentCategory: "ALL"
    property string currentSort: "newest"
    signal categorySelected(string category)
    signal sortSelected(string sort)

    // Category definitions
    ListModel {
        id: categoryModel
        ListElement { key: "ALL"; label: "全部" }
        ListElement { key: "DEFAULT"; label: "文本" }
        ListElement { key: "IMAGE"; label: "图片" }
        ListElement { key: "WORD"; label: "Word" }
        ListElement { key: "EXCEL"; label: "Excel" }
        ListElement { key: "PDF"; label: "PDF" }
        ListElement { key: "PPT"; label: "PPT" }
        ListElement { key: "ARCHIVE"; label: "压缩" }
    }

    Repeater {
        model: categoryModel

        CategoryButton {
            category: model.key
            label: model.label
            isActive: root.currentCategory === model.key
            onClicked: {
                root.currentCategory = model.key
                root.categorySelected(model.key)
            }
        }
    }

    Item { Layout.fillWidth: true }

    // Sort dropdown
    Rectangle {
        Layout.preferredWidth: sortLabel.implicitWidth + 24
        Layout.preferredHeight: 24
        radius: Theme.radiusSM
        color: sortMouse.containsMouse || sortDropdown.visible ? Theme.bgHover : "transparent"
        border.color: sortDropdown.visible ? Theme.borderHover : Theme.border
        border.width: 1

        Row {
            anchors.centerIn: parent
            spacing: 4

            Text {
                id: sortLabel
                text: {
                    switch (root.currentSort) {
                        case "newest": return "最新优先"
                        case "oldest": return "最早优先"
                        case "type": return "按类型"
                        case "source": return "按来源"
                        default: return "排序"
                    }
                }
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilyPrimary
                color: Theme.textTertiary
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "▾"
                font.pixelSize: 8
                color: Theme.textPlaceholder
                rotation: sortDropdown.visible ? 180 : 0
                anchors.verticalCenter: parent.verticalCenter

                Behavior on rotation {
                    NumberAnimation { duration: 150 }
                }
            }
        }

        MouseArea {
            id: sortMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: sortDropdown.visible = !sortDropdown.visible
        }

        // Dropdown
        Rectangle {
            id: sortDropdown
            visible: false
            anchors.top: parent.bottom
            anchors.right: parent.right
            anchors.topMargin: 4
            width: 120
            height: sortColumn.height + Theme.spacingXS * 2
            radius: Theme.radiusSM
            color: Theme.bgTertiary
            border.color: Theme.border
            border.width: 1
            z: 100

            Column {
                id: sortColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.spacingXS

                Repeater {
                    model: [
                        { key: "newest", label: "最新优先" },
                        { key: "oldest", label: "最早优先" },
                        { key: "type", label: "按类型" },
                        { key: "source", label: "按来源" },
                    ]

                    Rectangle {
                        width: sortColumn.width
                        height: 28
                        radius: Theme.radiusSM
                        color: optionMouse.containsMouse ? Theme.bgHover : "transparent"

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spacingSM
                            anchors.rightMargin: Theme.spacingSM
                            spacing: Theme.spacingXS

                            Text {
                                visible: root.currentSort === modelData.key
                                text: "✓"
                                font.pixelSize: 10
                                color: Theme.accentMint
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: modelData.label
                                font.pixelSize: Theme.fontSizeXS
                                font.family: Theme.fontFamilyPrimary
                                color: root.currentSort === modelData.key ? Theme.accentMint : Theme.textSecondary
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        MouseArea {
                            id: optionMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.currentSort = modelData.key
                                root.sortSelected(modelData.key)
                                sortDropdown.visible = false
                            }
                        }
                    }
                }
            }
        }
    }

    // Close dropdown when clicking outside
    MouseArea {
        anchors.fill: parent
        z: -1
        onPressed: sortDropdown.visible = false
    }
}
