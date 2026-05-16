"""Custom widget for displaying a single clipboard entry in the panel."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.models.clipboard_item import ClipboardItem, ContentType
from src.utils.helpers import format_timestamp, truncate_text

STYLE = """
ClipboardItemWidget {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 6px;
}
ClipboardItemWidget:hover {
    background: rgba(255, 255, 255, 0.15);
}
"""


class ClipboardItemWidget(QWidget):
    """Display widget for one clipboard item."""

    clicked = pyqtSignal(ClipboardItem)
    delete_clicked = pyqtSignal(int)
    pin_clicked = pyqtSignal(int)

    def __init__(self, item: ClipboardItem, parent: QWidget | None = None):
        super().__init__(parent)
        self.item = item
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(STYLE)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)

        # 类型图标
        type_icon = {ContentType.TEXT: "📝", ContentType.IMAGE: "🖼️",
                     ContentType.FILES: "📁", ContentType.HTML: "🌐"}
        icon_label = QLabel(type_icon.get(self.item.content_type, "📋"))
        icon_label.setFixedWidth(24)
        layout.addWidget(icon_label)

        # 图片缩略图
        if self.item.content_type == ContentType.IMAGE and self.item.thumbnail_path:
            thumb_label = QLabel()
            pixmap = QPixmap(self.item.thumbnail_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                thumb_label.setPixmap(scaled)
                thumb_label.setFixedSize(48, 48)
                layout.addWidget(thumb_label)

        # 内容预览
        preview_text = self.item.short_preview()
        preview = QLabel(truncate_text(preview_text, 60))
        preview.setFont(QFont("Microsoft YaHei", 9))
        preview.setWordWrap(True)
        layout.addWidget(preview, stretch=1)

        # 时间
        time_label = QLabel(format_timestamp(self.item.created_at))
        time_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(time_label)

        # 置顶按钮
        pin_btn = QPushButton("📌" if self.item.is_pinned else "📍")
        pin_btn.setFixedSize(24, 24)
        pin_btn.setStyleSheet("background: none; border: none; font-size: 14px;")
        pin_btn.clicked.connect(lambda: self.pin_clicked.emit(self.item.id))
        layout.addWidget(pin_btn)

        # 删除按钮
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet(
            "background: none; border: none; color: #ff6b6b; font-size: 12px;"
        )
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.item.id))
        layout.addWidget(del_btn)

    def mousePressEvent(self, event) -> None:  # type: ignore
        self.clicked.emit(self.item)
