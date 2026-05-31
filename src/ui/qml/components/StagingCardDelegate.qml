import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: card
    width: 96
    height: 96
    radius: Theme.radiusSM
    color: cardMouse.containsMouse ? Theme.bgHover : Theme.bgTertiary
    border.color: cardMouse.containsMouse ? Theme.borderHover : Theme.border
    border.width: 1

    // Model roles
    property int stagingId: model.id || 0
    property string contentType: model.contentType || "TEXT"
    property string contentText: model.contentText || ""
    property string filePath: model.filePath || ""
    property string thumbnailPath: model.thumbnailPath || ""
    property string displayType: model.displayType || "text"
    property string previewText: model.previewText || ""
    property string cardTitle: model.cardTitle || ""

    // Type color
    function typeColor() {
        switch (displayType) {
            case "word": return Theme.typeWord
            case "excel": return Theme.typeExcel
            case "pdf": return Theme.typePdf
            case "ppt": return Theme.typePpt
            case "archive": return Theme.typeArchive
            case "image": return Theme.typeImage
            case "html": return Theme.accentCyan
            default: return Theme.typeText
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingXS
        spacing: 2

        // Content area (thumbnail or icon)
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Image thumbnail
            Image {
                visible: thumbnailPath !== "" && contentType === "IMAGE"
                anchors.fill: parent
                anchors.margins: 2
                source: thumbnailPath ? "file:///" + thumbnailPath : ""
                fillMode: Image.PreserveAspectCrop
                clip: true
            }

            // Type icon for non-images
            Rectangle {
                visible: thumbnailPath === "" || contentType !== "IMAGE"
                anchors.fill: parent
                anchors.margins: 2
                radius: Theme.radiusSM
                color: Qt.rgba(1, 1, 1, 0.03)

                Column {
                    anchors.centerIn: parent
                    spacing: 2

                    Text {
                        text: displayType === "image" ? "🖼" :
                              displayType === "word" ? "W" :
                              displayType === "excel" ? "E" :
                              displayType === "pdf" ? "P" :
                              displayType === "ppt" ? "T" :
                              displayType === "html" ? "🌐" : "T"
                        font.pixelSize: 20
                        font.weight: Font.Bold
                        color: typeColor()
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: cardTitle
                        font.pixelSize: 8
                        font.family: Theme.fontFamilyPrimary
                        color: Theme.textSecondary
                        width: 80
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }
        }
    }

    // Hover overlay with actions
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSM
        color: "#80000000"
        visible: cardMouse.containsMouse || cardContextPopup.visible

        RowLayout {
            anchors.centerIn: parent
            spacing: Theme.spacingXS

            // Copy button
            Rectangle {
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                radius: Theme.radiusSM
                color: copyBtnMouse.containsMouse ? Theme.accentMint : "#40FFFFFF"

                Text {
                    anchors.centerIn: parent
                    text: "📋"
                    font.pixelSize: 12
                }

                MouseArea {
                    id: copyBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bridge.copyStagingItem(stagingId)
                }
            }

            // Remove button
            Rectangle {
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                radius: Theme.radiusSM
                color: removeBtnMouse.containsMouse ? Theme.error : "#40FFFFFF"

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    font.pixelSize: 12
                    color: Theme.textInverse
                }

                MouseArea {
                    id: removeBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bridge.removeFromStaging(stagingId)
                }
            }
        }
    }

    // Mouse area for hover and right-click
    MouseArea {
        id: cardMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                cardContextPopup.popup()
                return
            }
            // Left click = copy
            bridge.copyStagingItem(stagingId)
        }
    }

    // Context menu
    Menu {
        id: cardContextPopup

        MenuItem {
            text: "复制"
            onTriggered: bridge.copyStagingItem(stagingId)
        }
        MenuItem {
            text: "存回历史"
            onTriggered: bridge.stagingToHistory(stagingId)
        }
        MenuSeparator {}
        MenuItem {
            text: "移除"
            onTriggered: bridge.removeFromStaging(stagingId)
        }
    }
}
