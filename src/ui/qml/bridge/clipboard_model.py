"""QAbstractListModel subclass optimized for QML ListView binding."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, pyqtSlot

from src.models.clipboard_item import ClipboardItem, ContentType


_SOURCE_ICONS = {
    "clipboard": "📋",
    "context-menu": "📎",
    "drag-drop": "📥",
    "hotkey": "⌨️",
    "browser-plugin": "🌐",
    "api": "🔗",
}


def _format_time(ts: str | datetime | None) -> str:
    if ts is None:
        return ""
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except ValueError:
            return ts
    now = datetime.utcnow()
    delta = now - ts
    if delta.total_seconds() < 60:
        return "刚刚"
    if delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds() // 60)} 分钟前"
    if delta.days == 0:
        return ts.strftime("%H:%M")
    return ts.strftime("%m-%d %H:%M")


def _short_preview(item: ClipboardItem, max_len: int = 80) -> str:
    if item.content_type == ContentType.TEXT:
        return (item.content_text or "")[:max_len].replace("\n", " ")
    if item.content_type == ContentType.IMAGE:
        if item.file_path:
            return Path(item.file_path).stem
        return "图片"
    if item.content_type == ContentType.FILES:
        paths = (item.content_text or "").split("\n")
        names = [Path(p).name for p in paths if p.strip()]
        if len(names) > 2:
            return f"{names[0]} 等 {len(names)} 个文件"
        return " ".join(names) if names else "文件"
    if item.content_type == ContentType.HTML:
        text = re.sub(r"<[^>]+>", "", item.content_html or "")
        return text[:max_len].replace("\n", " ")
    return ""


def _extract_filename(item: ClipboardItem) -> str:
    """Extract a display-friendly filename for the main title."""
    if item.content_type == ContentType.TEXT:
        preview = (item.content_text or "")[:60].replace("\n", " ")
        return preview if preview else "文本"
    if item.content_type == ContentType.IMAGE:
        if item.file_path:
            stem = Path(item.file_path).stem
            return stem if stem and not stem.startswith("thumb_") else "图片"
        return "图片"
    if item.content_type == ContentType.FILES:
        # Try file_path first, fall back to first line of content_text
        fp = item.file_path or (item.content_text or "").split("\n")[0].strip()
        if fp:
            return Path(fp).name
        return "文件"
    if item.content_type == ContentType.HTML:
        text = re.sub(r"<[^>]+>", "", item.content_html or "")
        preview = text[:60].replace("\n", " ")
        return preview if preview else "HTML"
    return ""


def _file_path_display(item: ClipboardItem) -> str:
    """Extract a secondary path/folder display string."""
    if item.content_type == ContentType.FILES:
        paths = (item.content_text or "").split("\n")
        count = len([p for p in paths if p.strip()])
        if count > 1:
            return f"共 {count} 个文件"
        # Single file: show parent folder name
        fp = item.file_path or (paths[0].strip() if paths else "")
        if fp:
            parent = Path(fp).parent
            return parent.name if parent.name else ""
        return ""
    return ""


def _source_icon(source: str) -> str:
    return _SOURCE_ICONS.get(source, "📋")


class QClipboardListModel(QAbstractListModel):
    """List model exposing named roles for QML delegates."""

    IdRole = Qt.ItemDataRole.UserRole + 1
    ContentTextRole = Qt.ItemDataRole.UserRole + 2
    ContentTypeRole = Qt.ItemDataRole.UserRole + 3
    FilePathRole = Qt.ItemDataRole.UserRole + 4
    ThumbnailPathRole = Qt.ItemDataRole.UserRole + 5
    IsPinnedRole = Qt.ItemDataRole.UserRole + 6
    IsFavoriteRole = Qt.ItemDataRole.UserRole + 7
    IsStarredRole = Qt.ItemDataRole.UserRole + 8
    CreatedAtRole = Qt.ItemDataRole.UserRole + 9
    SourceRole = Qt.ItemDataRole.UserRole + 10
    TagsRole = Qt.ItemDataRole.UserRole + 11
    CategoryRole = Qt.ItemDataRole.UserRole + 12
    PreviewTextRole = Qt.ItemDataRole.UserRole + 13
    TimeTextRole = Qt.ItemDataRole.UserRole + 14
    SourceIconRole = Qt.ItemDataRole.UserRole + 15
    DisplayTypeRole = Qt.ItemDataRole.UserRole + 16
    FileNameRole = Qt.ItemDataRole.UserRole + 17
    FilePathDisplayRole = Qt.ItemDataRole.UserRole + 18

    _ROLE_NAMES: dict[int, bytes] = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[ClipboardItem] = []

    def roleNames(self) -> dict[int, QByteArray]:
        if not self._ROLE_NAMES:
            names = {
                self.IdRole: b"id",
                self.ContentTextRole: b"contentText",
                self.ContentTypeRole: b"contentType",
                self.FilePathRole: b"filePath",
                self.ThumbnailPathRole: b"thumbnailPath",
                self.IsPinnedRole: b"isPinned",
                self.IsFavoriteRole: b"isFavorite",
                self.IsStarredRole: b"isStarred",
                self.CreatedAtRole: b"createdAt",
                self.SourceRole: b"source",
                self.TagsRole: b"tags",
                self.CategoryRole: b"category",
                self.PreviewTextRole: b"previewText",
                self.TimeTextRole: b"timeText",
                self.SourceIconRole: b"sourceIcon",
                self.DisplayTypeRole: b"displayType",
                self.FileNameRole: b"fileName",
                self.FilePathDisplayRole: b"filePathDisplay",
            }
            QClipboardListModel._ROLE_NAMES = {
                k: QByteArray(v) for k, v in names.items()
            }
        return self._ROLE_NAMES

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        match role:
            case self.IdRole:
                return item.id
            case self.ContentTextRole:
                return item.content_text or ""
            case self.ContentTypeRole:
                return item.content_type.value if item.content_type else "TEXT"
            case self.FilePathRole:
                return item.file_path or ""
            case self.ThumbnailPathRole:
                return item.thumbnail_path or ""
            case self.IsPinnedRole:
                return item.is_pinned
            case self.IsFavoriteRole:
                return item.is_favorite
            case self.IsStarredRole:
                return item.is_starred
            case self.CreatedAtRole:
                return str(item.created_at) if item.created_at else ""
            case self.SourceRole:
                return item.source or "clipboard"
            case self.TagsRole:
                return [
                    {"id": t.id, "name": t.name, "color": t.color}
                    for t in (item.tags or [])
                ]
            case self.CategoryRole:
                return item.category or "DEFAULT"
            case self.PreviewTextRole:
                return _short_preview(item)
            case self.TimeTextRole:
                return _format_time(item.created_at)
            case self.SourceIconRole:
                return _source_icon(item.source or "clipboard")
            case self.DisplayTypeRole:
                return item.display_type
            case self.FileNameRole:
                return _extract_filename(item)
            case self.FilePathDisplayRole:
                return _file_path_display(item)
        return None

    @pyqtSlot(list)
    def setItems(self, items: list) -> None:
        """Replace all items with a new list (called from QmlBridge)."""
        self.beginResetModel()
        self._items = items if isinstance(items, list) else list(items)
        self.endResetModel()

    def get_item(self, row: int) -> Optional[ClipboardItem]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_items(self) -> list[ClipboardItem]:
        return list(self._items)

    def get_item_by_id(self, item_id: int) -> Optional[ClipboardItem]:
        for item in self._items:
            if item.id == item_id:
                return item
        return None
