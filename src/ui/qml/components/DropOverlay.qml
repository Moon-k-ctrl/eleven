import QtQuick 2.15
import QtQuick.Layouts 1.15

DropArea {
    id: root
    anchors.fill: parent

    property bool dragActive: false

    onEntered: { dragActive = true }
    onExited: { dragActive = false }
    onDropped: function(drop) {
        dragActive = false
        if (drop.hasUrls) {
            var paths = []
            for (var i = 0; i < drop.urls.length; i++) {
                var url = drop.urls[i]
                var path = ""
                
                // QML URL to local path conversion
                var urlStr = ""
                if (url !== null && url !== undefined) {
                    if (typeof url.toLocalFile === "function") {
                        path = url.toLocalFile()
                    }
                    if (!path) {
                        urlStr = url.toString()
                    }
                }
                
                if (!path && urlStr) {
                    // Remove file:/// or file:// prefix
                    if (urlStr.indexOf("file:///") === 0) {
                        path = decodeURIComponent(urlStr.substring(8))
                    } else if (urlStr.indexOf("file://") === 0) {
                        path = decodeURIComponent(urlStr.substring(7))
                    } else {
                        path = decodeURIComponent(urlStr)
                    }
                    
                    // Windows path normalization: /C:/Users/... -> C:/Users/...
                    if (path.charAt(0) === '/' && path.charAt(2) === ':') {
                        path = path.substring(1)
                    }
                }
                
                if (path) {
                    paths.push(path)
                }
            }
            if (paths.length > 0) {
                bridge.importFiles(paths)
                bridge.refreshList()
            }
        }
    }

    // Visual overlay
    Rectangle {
        anchors.fill: parent
        visible: root.dragActive
        color: "#127CE0C3" // accentMint at 7%
        border.color: Theme.accentMint
        border.width: 2
        radius: Theme.radiusMD

        // Dashed border effect
        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            color: "transparent"
            border.color: Qt.rgba(0.49, 0.88, 0.76, 0.3)
            border.width: 1
            radius: Theme.radiusSM

            // Use a Canvas for dashed line
            Canvas {
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.strokeStyle = Qt.rgba(0.49, 0.88, 0.76, 0.4)
                    ctx.lineWidth = 1
                    ctx.setLineDash([4, 4])
                    ctx.beginPath()
                    ctx.roundedRect(0, 0, width, height, 6, 6)
                    ctx.stroke()
                }
            }
        }

        ColumnLayout {
            anchors.centerIn: parent
            spacing: Theme.spacingSM

            Text {
                text: "📥"
                font.pixelSize: 32
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: "拖拽文件到这里导入"
                font.pixelSize: Theme.fontSizeMD
                font.family: Theme.fontFamilyPrimary
                color: Theme.accentMint
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
