import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    height: Theme.searchBarHeight
    radius: Theme.radiusMD
    color: "#0BFFFFFF"
    border.color: searchInput.activeFocus ? Theme.accentMint : Theme.lineSoft
    border.width: 1

    property alias text: searchInput.text

    function forceActiveFocus() {
        searchInput.forceActiveFocus()
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingSM
        anchors.rightMargin: Theme.spacingSM
        spacing: Theme.spacingXS

        Text {
            text: Theme.iconSearch
            font.pixelSize: Theme.fontSizeMD
            color: Theme.textPlaceholder
            Layout.alignment: Qt.AlignVCenter
        }

        TextInput {
            id: searchInput
            Layout.fillWidth: true
            font.pixelSize: Theme.fontSizeMD
            font.family: Theme.fontFamilyPrimary
            color: Theme.textPrimary
            clip: true
            selectByMouse: true
            selectionColor: Qt.rgba(0.49, 0.88, 0.76, 0.25) // accentMint at 25%

            Text {
                visible: !searchInput.text && !searchInput.activeFocus
                text: "搜索剪贴内容..."
                font: searchInput.font
                color: Theme.textPlaceholder
                anchors.verticalCenter: parent.verticalCenter
            }

            onTextChanged: bridge.searchTextChanged(text)
            Keys.onEscapePressed: {
                if (text) { text = "" } else { /* handled by parent */ }
            }
            Keys.onReturnPressed: bridge.doSearch()
        }

        // Clear button
        Text {
            visible: searchInput.text.length > 0
            text: "✕"
            font.pixelSize: Theme.fontSizeSM
            color: Theme.textTertiary
            Layout.alignment: Qt.AlignVCenter

            MouseArea {
                anchors.fill: parent
                anchors.margins: -4
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    searchInput.text = ""
                    bridge.clearSearch()
                    searchInput.forceActiveFocus()
                }
            }
        }
    }
}
