import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    color: Theme.bgSecondary
    radius: Theme.radiusMD
    border.color: Theme.lineSoft
    border.width: 1

    property var phrases: []
    property bool editing: false
    property int editId: -1

    function refresh() {
        phrases = bridge.getPhrases()
    }

    Component.onCompleted: refresh()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingSM
        spacing: Theme.spacingXS

        // Header
        RowLayout {
            Layout.fillWidth: true

            Text {
                text: "⚡ 常用短语"
                font.pixelSize: Theme.fontSizeMD
                font.weight: Theme.fontBold
                font.family: Theme.fontFamilyPrimary
                color: Theme.textPrimary
            }

            Text {
                text: phrases.length + " 条"
                font.pixelSize: Theme.fontSizeXS
                font.family: Theme.fontFamilySecondary
                color: Theme.textPlaceholder
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                Layout.preferredWidth: addBtnText.implicitWidth + Theme.spacingSM * 2
                Layout.preferredHeight: 24
                radius: Theme.radiusSM
                color: addBtnMouse.containsMouse ? Theme.accentMint : Qt.rgba(0.49, 0.88, 0.76, 0.15)
                border.color: Theme.accentMint
                border.width: 1

                Text {
                    id: addBtnText
                    anchors.centerIn: parent
                    text: "+ 添加"
                    font.pixelSize: Theme.fontSizeXS
                    font.family: Theme.fontFamilyPrimary
                    color: addBtnMouse.containsMouse ? Theme.textInverse : Theme.accentMint
                }

                MouseArea {
                    id: addBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        editing = true
                        editId = -1
                        nameInput.text = ""
                        contentInput.text = ""
                    }
                }
            }
        }

        // Phrase list
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            model: phrases

            delegate: Rectangle {
                width: ListView.view.width
                height: 52
                radius: Theme.radiusSM
                color: phraseMouse.containsMouse ? Theme.bgHover : Theme.bgTertiary
                border.color: phraseMouse.containsMouse ? Theme.borderHover : Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingSM
                    spacing: Theme.spacingSM

                    // Color dot
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: modelData.color || Theme.accentMint
                    }

                    // Name + preview
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: modelData.name || ""
                            font.pixelSize: Theme.fontSizeSM
                            font.weight: Theme.fontBold
                            font.family: Theme.fontFamilyPrimary
                            color: Theme.textPrimary
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        Text {
                            text: (modelData.content || "").substring(0, 50)
                            font.pixelSize: Theme.fontSizeXS
                            font.family: Theme.fontFamilyPrimary
                            color: Theme.textTertiary
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    // Use count
                    Text {
                        visible: (modelData.use_count || 0) > 0
                        text: "×" + (modelData.use_count || 0)
                        font.pixelSize: 9
                        font.family: Theme.fontFamilySecondary
                        color: Theme.textPlaceholder
                    }

                    // Actions (visible on hover)
                    Row {
                        spacing: 4
                        visible: phraseMouse.containsMouse

                        Rectangle {
                            width: 20
                            height: 20
                            radius: 4
                            color: editBtnMouse.containsMouse ? Theme.bgActive : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: "✏"
                                font.pixelSize: 10
                            }

                            MouseArea {
                                id: editBtnMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    editing = true
                                    editId = modelData.id
                                    nameInput.text = modelData.name || ""
                                    contentInput.text = modelData.content || ""
                                }
                            }
                        }

                        Rectangle {
                            width: 20
                            height: 20
                            radius: 4
                            color: delBtnMouse.containsMouse ? Qt.rgba(0.94, 0.39, 0.39, 0.2) : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: "✕"
                                font.pixelSize: 10
                                color: delBtnMouse.containsMouse ? Theme.error : Theme.textTertiary
                            }

                            MouseArea {
                                id: delBtnMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    bridge.deletePhrase(modelData.id)
                                    root.refresh()
                                }
                            }
                        }
                    }
                }

                MouseArea {
                    id: phraseMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        bridge.usePhrase(modelData.id)
                    }
                }
            }

            // Empty state
            Text {
                visible: phrases.length === 0
                anchors.centerIn: parent
                text: "暂无常用短语\n点击「+ 添加」创建第一条"
                font.pixelSize: Theme.fontSizeSM
                font.family: Theme.fontFamilyPrimary
                color: Theme.textPlaceholder
                horizontalAlignment: Text.AlignHCenter
            }
        }

        // Edit area (visible when adding/editing)
        Rectangle {
            visible: editing
            Layout.fillWidth: true
            height: editColumn.height + Theme.spacingSM * 2
            radius: Theme.radiusSM
            color: Theme.bgTertiary
            border.color: Theme.border
            border.width: 1

            ColumnLayout {
                id: editColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.spacingSM
                spacing: Theme.spacingXS

                TextInput {
                    id: nameInput
                    Layout.fillWidth: true
                    font.pixelSize: Theme.fontSizeSM
                    font.family: Theme.fontFamilyPrimary
                    color: Theme.textPrimary
                    clip: true

                    Text {
                        visible: !nameInput.text && !nameInput.activeFocus
                        text: "短语名称"
                        font: nameInput.font
                        color: Theme.textPlaceholder
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.lineSoft
                }

                TextInput {
                    id: contentInput
                    Layout.fillWidth: true
                    font.pixelSize: Theme.fontSizeXS
                    font.family: Theme.fontFamilyPrimary
                    color: Theme.textSecondary
                    clip: true

                    Text {
                        visible: !contentInput.text && !contentInput.activeFocus
                        text: "短语内容"
                        font: contentInput.font
                        color: Theme.textPlaceholder
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingXS

                    Rectangle {
                        Layout.preferredWidth: 50
                        Layout.preferredHeight: 24
                        radius: Theme.radiusSM
                        color: saveBtnMouse.containsMouse ? Theme.accentMint : Qt.rgba(0.49, 0.88, 0.76, 0.15)

                        Text {
                            anchors.centerIn: parent
                            text: "保存"
                            font.pixelSize: Theme.fontSizeXS
                            font.family: Theme.fontFamilyPrimary
                            color: saveBtnMouse.containsMouse ? Theme.textInverse : Theme.accentMint
                        }

                        MouseArea {
                            id: saveBtnMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (nameInput.text && contentInput.text) {
                                    if (editId >= 0) {
                                        bridge.updatePhrase(editId, nameInput.text, contentInput.text, "#7CE0C3")
                                    } else {
                                        bridge.createPhrase(nameInput.text, contentInput.text, "#7CE0C3")
                                    }
                                    editing = false
                                    root.refresh()
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 50
                        Layout.preferredHeight: 24
                        radius: Theme.radiusSM
                        color: cancelBtnMouse.containsMouse ? Theme.bgHover : "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "取消"
                            font.pixelSize: Theme.fontSizeXS
                            font.family: Theme.fontFamilyPrimary
                            color: Theme.textTertiary
                        }

                        MouseArea {
                            id: cancelBtnMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: editing = false
                        }
                    }

                    Item { Layout.fillWidth: true }
                }
            }
        }
    }
}
