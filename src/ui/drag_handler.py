"""Drag-out handler for clipboard items."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QMimeData, QPoint, Qt
from PyQt6.QtGui import QDrag, QPixmap

from src.models.clipboard_item import ClipboardItem, ContentType


class DragHandler:
    """Handles drag-out operations for clipboard items."""

    @staticmethod
    def start_drag(item: ClipboardItem, parent_widget) -> Optional[QDrag]:
        """Start a drag operation for the given item.

        Returns the QDrag object, or None if the item type is not supported.
        """
        mime_data = DragHandler._create_mime_data(item)
        if mime_data is None:
            return None

        drag = QDrag(parent_widget)
        drag.setMimeData(mime_data)

        # 设置拖拽图标
        pixmap = DragHandler._create_drag_pixmap(item)
        if pixmap:
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # 执行拖拽（非阻塞）
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

        return drag

    @staticmethod
    def _create_mime_data(item: ClipboardItem) -> Optional[QMimeData]:
        """Create MIME data for the item."""
        mime_data = QMimeData()

        if item.content_type == ContentType.TEXT and item.content_text:
            mime_data.setText(item.content_text)
            return mime_data

        elif item.content_type == ContentType.HTML:
            if item.content_html:
                mime_data.setHtml(item.content_html)
            if item.content_text:
                mime_data.setText(item.content_text)
            return mime_data

        elif item.content_type == ContentType.FILES and item.content_text:
            files = item.content_text.split("\n")
            urls = [f"file:///{f}" for f in files]
            from PyQt6.QtCore import QUrl
            mime_data.setUrls([QUrl(u) for u in urls])
            return mime_data

        elif item.content_type == ContentType.IMAGE and item.file_path:
            # 图片：提供文件 URL 和原始数据
            from PyQt6.QtCore import QUrl
            mime_data.setUrls([QUrl.fromLocalFile(item.file_path)])

            # 同时提供 PNG 数据
            try:
                with open(item.file_path, "rb") as f:
                    mime_data.setData("image/png", f.read())
            except OSError:
                pass

            return mime_data

        return None

    @staticmethod
    def _create_drag_pixmap(item: ClipboardItem) -> Optional[QPixmap]:
        """Create a drag preview pixmap."""
        if item.content_type == ContentType.IMAGE and item.thumbnail_path:
            pixmap = QPixmap(item.thumbnail_path)
            if not pixmap.isNull():
                return pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)

        # 对于其他类型，返回 None（使用默认图标）
        return None

    # ── v4.0 多选拖出 ──

    @staticmethod
    def start_multi_drag(items: list[ClipboardItem], parent_widget) -> Optional[QDrag]:
        """Drag out multiple items. Files merged as URL list, texts concatenated."""
        if not items:
            return None

        from PyQt6.QtCore import QUrl

        mime_data = QMimeData()
        file_urls: list[QUrl] = []
        text_parts: list[str] = []

        for item in items:
            if item.content_type == ContentType.FILES and item.content_text:
                for fp in item.content_text.split("\n"):
                    file_urls.append(QUrl.fromLocalFile(fp))
            elif item.content_type == ContentType.IMAGE and item.file_path:
                file_urls.append(QUrl.fromLocalFile(item.file_path))
            elif item.content_type == ContentType.TEXT and item.content_text:
                text_parts.append(item.content_text)
            elif item.content_type == ContentType.HTML and item.content_text:
                text_parts.append(item.content_text)

        if file_urls:
            mime_data.setUrls(file_urls)
        if text_parts:
            mime_data.setText("\n---\n".join(text_parts))

        if mime_data.isEmpty():
            return None

        drag = QDrag(parent_widget)
        drag.setMimeData(mime_data)

        pixmap = DragHandler._create_multi_drag_pixmap(items)
        if pixmap:
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.exec(Qt.DropAction.CopyAction)
        return drag

    @staticmethod
    def _create_multi_drag_pixmap(items: list[ClipboardItem]) -> Optional[QPixmap]:
        """Stacked thumbnail preview for multi-drag (max 3, with offset)."""
        size = 48
        offset = 8
        count = min(len(items), 3)
        w = size + offset * (count - 1)
        h = size + offset * (count - 1)
        canvas = QPixmap(w, h)
        canvas.fill(Qt.GlobalColor.transparent)

        from PyQt6.QtGui import QPainter
        painter = QPainter(canvas)
        for i in range(count):
            item = items[i]
            x, y = i * offset, i * offset
            if item.thumbnail_path:
                thumb = QPixmap(item.thumbnail_path)
                if not thumb.isNull():
                    thumb = thumb.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    painter.drawPixmap(x, y, thumb)
                    continue
            from PyQt6.QtGui import QColor
            painter.fillRect(x, y, size, size, QColor(60, 60, 60))
            from PyQt6.QtCore import QRect
            painter.drawText(QRect(x, y, size, size), Qt.AlignmentFlag.AlignCenter, "📄")
        painter.end()
        return canvas
