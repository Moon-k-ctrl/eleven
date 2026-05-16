"""Delegate for rendering clipboard items in the virtual list."""
from __future__ import annotations

import time

from PyQt6.QtCore import QModelIndex, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QMenu, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget

from src.models.clipboard_item import ClipboardItem, ContentType, Source, Tag
from src.ui.drag_handler import DragHandler
from src.utils.helpers import format_timestamp, truncate_text


class ClipboardItemDelegate(QStyledItemDelegate):
    """Delegate for rendering clipboard items."""

    item_clicked = pyqtSignal(ClipboardItem)
    delete_clicked = pyqtSignal(int)
    pin_clicked = pyqtSignal(int)
    drag_started = pyqtSignal(ClipboardItem)
    tag_add_requested = pyqtSignal(int, int)
    tag_remove_requested = pyqtSignal(int, int)
    preview_requested = pyqtSignal(ClipboardItem)
    export_requested = pyqtSignal(list)
    favorite_toggled = pyqtSignal(int)
    star_toggled = pyqtSignal(int)
    multi_select_toggled = pyqtSignal()
    selection_toggled = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item_height = 72
        self._drag_start_pos: QPoint | None = None
        self._drag_item: ClipboardItem | None = None
        self._all_tags: list[Tag] = []
        # 多选模式
        self._multi_select_mode: bool = False
        self._selected_ids: set[int] = set()
        # 双击检测
        self._last_click_time: float = 0
        self._last_click_index: QModelIndex | None = None
        self._pending_click_item: ClipboardItem | None = None
        # v4.0 拖出视觉反馈
        self._dragging_ids: set[int] = set()

    def set_all_tags(self, tags: list[Tag]) -> None:
        self._all_tags = tags

    def set_multi_select(self, mode: bool, selected_ids: set[int]) -> None:
        self._multi_select_mode = mode
        self._selected_ids = selected_ids

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        item = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(item, ClipboardItem):
            return super().paint(painter, option, index)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        r = option.rect

        # v4.0 拖出半透明反馈
        if self._dragging_ids and item.id in self._dragging_ids:
            painter.setOpacity(0.4)

        # 背景
        is_selected = item.id is not None and item.id in self._selected_ids
        if self._multi_select_mode and is_selected:
            painter.fillRect(r, QColor(176, 141, 87, 64))  # 金色半透明高亮
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(r, QColor(255, 255, 255, 10))  # 白色4%透明
        else:
            painter.fillRect(r, QColor(30, 30, 30))

        # 恢复正常透明度（仅背景半透明）
        painter.setOpacity(1.0)

        # 多选模式复选框
        checkbox_x = r.left() + 4
        if self._multi_select_mode:
            painter.setPen(QColor(100, 100, 100))
            painter.setBrush(QColor(30, 30, 30) if not is_selected else QColor(176, 141, 87))
            cb_rect = QRect(checkbox_x, r.top() + 26, 16, 16)
            painter.drawRect(cb_rect)
            if is_selected:
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
                painter.drawText(cb_rect, Qt.AlignmentFlag.AlignCenter, "✓")
            icon_left = checkbox_x + 24
        else:
            icon_left = r.left() + 8

        # 左侧 48x48 类型图标/缩略图
        icon_rect = QRect(icon_left, r.top() + 12, 48, 48)
        self._paint_type_icon(painter, icon_rect, item)
        content_left = icon_left + 56

        # 置顶标记
        pin_x = r.right() - 24 if item.is_pinned else r.right()

        # 删除按钮区域（右侧）
        del_x = pin_x - 24

        # 收藏标记
        fav_x = del_x - 20 if item.is_favorite else del_x

        # v3.0 星标标记（在收藏左侧）
        star_x = fav_x - 20 if item.is_starred else fav_x

        # 第一行：内容预览
        preview_text = self._get_preview_text(item)
        painter.setFont(QFont("Microsoft YaHei", 10))
        painter.setPen(QColor(232, 232, 232))
        text_width = max(0, del_x - content_left - 12)
        if text_width > 0:
            painter.drawText(content_left, r.top() + 24, text_width, 20,
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                            preview_text)

        # 时间
        time_text = format_timestamp(item.created_at)
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor(136, 136, 136))
        painter.drawText(content_left, r.top() + 48, time_text)

        # 置顶图标
        if item.is_pinned:
            painter.setPen(QColor(176, 141, 87))  # 品牌金
            painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
            painter.drawText(pin_x, r.top() + 8, 20, 20,
                           Qt.AlignmentFlag.AlignCenter, "P")

        # 收藏图标
        if item.is_favorite:
            painter.setPen(QColor(196, 147, 74))  # accent-yellow
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.drawText(fav_x, r.top() + 8, 16, 20,
                           Qt.AlignmentFlag.AlignCenter, "★")

        # v3.0 星标图标
        if item.is_starred:
            painter.setPen(QColor(196, 147, 74))  # accent-yellow
            painter.setFont(QFont("Microsoft YaHei", 8))
            painter.drawText(star_x, r.top() + 8, 16, 20,
                           Qt.AlignmentFlag.AlignCenter, "⭐")

        # v3.0 来源指示器
        source_icons = {
            "clipboard": "📋", "context-menu": "📎", "drag-drop": "📥",
            "hotkey": "⌨️", "browser-plugin": "🌐", "api": "🔗",
        }
        source_icon = source_icons.get(item.source, "")
        if source_icon:
            time_text_measure = format_timestamp(item.created_at)
            fm = painter.fontMetrics()
            time_w = fm.horizontalAdvance(time_text_measure)
            source_x = content_left + time_w + 12
            painter.setFont(QFont("Microsoft YaHei", 7))
            painter.drawText(source_x, r.top() + 48, 16, 16,
                           Qt.AlignmentFlag.AlignCenter, source_icon)

        # 标签
        if item.tags:
            tag_y = r.top() + 48
            tag_x = max(content_left + 80, content_left + len(time_text) * 6 + 20)
            for tag in item.tags[:3]:
                fm = painter.fontMetrics()
                chip_w = fm.horizontalAdvance(tag.name) + 12
                chip_rect = QRect(tag_x, tag_y, chip_w, 16)
                painter.setBrush(QColor(tag.color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(chip_rect, 14, 14)
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Microsoft YaHei", 7))
                painter.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, tag.name)
                tag_x += chip_w + 4

        painter.restore()

    # File extension → (accent_color, label)
    _FILE_TYPE_STYLES: dict[str, tuple[str, str]] = {
        ".doc": ("#5B8DEF", "W"), ".docx": ("#5B8DEF", "W"),
        ".xls": ("#3A8B40", "X"), ".xlsx": ("#3A8B40", "X"),
        ".pdf": ("#C94043", "P"),
        ".ppt": ("#C4934A", "P"), ".pptx": ("#C4934A", "P"),
        ".zip": ("#C4934A", "Z"), ".rar": ("#C4934A", "Z"),
        ".7z": ("#C4934A", "Z"), ".tar": ("#C4934A", "Z"), ".gz": ("#C4934A", "Z"),
        ".txt": ("#4A90D9", "T"), ".log": ("#4A90D9", "T"),
        ".md": ("#4A90D9", "M"),
    }

    def _paint_type_icon(self, painter: QPainter, rect: QRect, item: ClipboardItem):
        """Paint 40x40 type icon or thumbnail."""
        # Try thumbnail for IMAGE
        if item.content_type == ContentType.IMAGE and item.thumbnail_path:
            pix = QPixmap(item.thumbnail_path)
            if not pix.isNull():
                scaled = pix.scaled(rect.width(), rect.height(),
                                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                    Qt.TransformationMode.SmoothTransformation)
                painter.save()
                path = QPainterPath()
                path.addRoundedRect(float(rect.x()), float(rect.y()),
                                    float(rect.width()), float(rect.height()), 10, 10)
                painter.setClipPath(path)
                painter.drawPixmap(rect, scaled)
                painter.restore()
                return

        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(42, 42, 42))
        painter.drawRoundedRect(rect, 10, 10)

        # For FILES type, draw file-type-specific icon
        if item.content_type == ContentType.FILES and item.content_text:
            ext = self._get_file_ext(item.content_text).lower()
            ext_dot = f".{ext}" if ext else ""
            color, label = self._FILE_TYPE_STYLES.get(ext_dot, ("#78909C", "F"))
            self._paint_file_icon(painter, rect, QColor(color), label, ext)
            return

        # For other types, use emoji
        type_icons = {
            ContentType.TEXT: "📝",
            ContentType.HTML: "🌐",
            ContentType.IMAGE: "🖼️",
        }
        icon = type_icons.get(item.content_type, "📄")
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI Emoji", 18))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, icon)

    def _paint_file_icon(self, painter: QPainter, rect: QRect,
                         color: QColor, label: str, ext: str):
        """Draw a file-type-specific icon with colored accent."""
        from PyQt6.QtCore import QRectF

        # Document body (rounded rect)
        body = QRectF(rect.x() + 6, rect.y() + 2, rect.width() - 12, rect.height() - 8)
        path = QPainterPath()
        path.addRoundedRect(body, 8, 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color.lighter(130))
        painter.drawPath(path)

        # Folded corner
        corner_size = 8
        corner = QPainterPath()
        corner.moveTo(body.right() - corner_size, body.top())
        corner.lineTo(body.right(), body.top() + corner_size)
        corner.lineTo(body.right() - corner_size, body.top() + corner_size)
        corner.closeSubpath()
        painter.setBrush(color.lighter(160))
        painter.drawPath(corner)

        # Label letter (center)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        label_rect = QRectF(body.x(), body.y() + 2, body.width(), body.height() - 12)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

        # Extension text (bottom)
        if ext:
            painter.setFont(QFont("Microsoft YaHei", 7))
            painter.setPen(QColor(200, 200, 200))
            ext_rect = QRectF(rect.x(), rect.bottom() - 12, rect.width(), 10)
            painter.drawText(ext_rect, Qt.AlignmentFlag.AlignCenter, ext.upper())

    def _get_file_ext(self, content_text: str) -> str:
        import os
        first_line = content_text.split("\n")[0]
        return os.path.splitext(first_line)[1].upper().lstrip(".")

    def _get_preview_text(self, item: ClipboardItem) -> str:
        """Get display text based on content type."""
        import os
        if item.content_type == ContentType.FILES and item.content_text:
            files = item.content_text.split("\n")
            first = os.path.basename(files[0])
            if len(files) > 1:
                return f"{first} 等 {len(files)} 个文件"
            return first
        if item.content_type == ContentType.IMAGE:
            parts = []
            if item.file_path:
                parts.append(os.path.basename(item.file_path))
            return " ".join(parts) or "图片"
        return truncate_text(item.short_preview(), 80)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(-1, self._item_height)

    def editorEvent(self, event, model, option, index):
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                item = index.data(Qt.ItemDataRole.UserRole)
                if not isinstance(item, ClipboardItem):
                    return False

                self._drag_start_pos = event.pos()
                self._drag_item = item

                x = int(event.position().x())
                y = int(event.position().y())

                # 多选模式：左键切换选中
                if self._multi_select_mode:
                    if item.id is not None:
                        self.selection_toggled.emit(item.id)
                    return True

                # 置顶按钮
                pin_rect = QRect(option.rect.right() - 24, option.rect.top() + 8, 20, 20)
                if pin_rect.contains(x, y):
                    self.pin_clicked.emit(item.id)
                    return True

                # 删除按钮
                del_rect = QRect(option.rect.right() - 48, option.rect.top() + 8, 20, 20)
                if del_rect.contains(x, y):
                    self.delete_clicked.emit(item.id)
                    return True

                # v3.0 星标按钮
                pin_r = option.rect.right() - 24 if item.is_pinned else option.rect.right()
                del_r = pin_r - 24
                fav_r = del_r - 20 if item.is_favorite else del_r
                star_rect = QRect(fav_r - 20, option.rect.top() + 8, 16, 20)
                if item.is_starred and star_rect.contains(x, y):
                    self.star_toggled.emit(item.id)
                    return True

                # 双击检测
                now = time.time()
                if (self._last_click_index is not None
                    and self._last_click_index == index
                    and now - self._last_click_time < 0.35):
                    # 双击 → 预览
                    self._last_click_time = 0
                    self._last_click_index = None
                    self.preview_requested.emit(item)
                    return True

                # 单击 → 复制
                self._last_click_time = now
                self._last_click_index = index
                self.item_clicked.emit(item)
                return True

            elif event.button() == Qt.MouseButton.RightButton:
                item = index.data(Qt.ItemDataRole.UserRole)
                if not isinstance(item, ClipboardItem) or item.id is None:
                    return False
                if self._multi_select_mode:
                    # 多选模式右键切换选中
                    self.selection_toggled.emit(item.id)
                    return True
                self._show_context_menu(item, event)
                return True

        elif event.type() == event.Type.MouseMove:
            if self._drag_start_pos is not None and self._drag_item is not None:
                distance = (event.pos() - self._drag_start_pos).manhattanLength()
                if distance > 10:
                    parent = self.parent()
                    if isinstance(parent, QWidget):
                        # v4.0 多选拖出
                        selected = parent.selectionModel().selectedIndexes()
                        if len(selected) > 1:
                            drag_items = [
                                idx.data(Qt.ItemDataRole.UserRole)
                                for idx in selected
                            ]
                            drag_items = [i for i in drag_items if isinstance(i, ClipboardItem)]
                            if drag_items:
                                self._dragging_ids = {i.id for i in drag_items if i.id}
                                parent.viewport().update()
                                DragHandler.start_multi_drag(drag_items, parent)
                                self._dragging_ids.clear()
                                parent.viewport().update()
                        else:
                            DragHandler.start_drag(self._drag_item, parent)
                        self.drag_started.emit(self._drag_item)
                    self._drag_start_pos = None
                    self._drag_item = None
                    return True

        elif event.type() == event.Type.MouseButtonRelease:
            self._drag_start_pos = None
            self._drag_item = None

        return False

    def _show_context_menu(self, item: ClipboardItem, event) -> None:
        menu = QMenu()

        # 复制
        copy_action = menu.addAction("复制")
        copy_action.setData("copy")

        # 预览
        preview_action = menu.addAction("预览")
        preview_action.setData("preview")

        menu.addSeparator()

        # 收藏
        fav_label = "取消收藏" if item.is_favorite else "收藏"
        fav_action = menu.addAction(fav_label)
        fav_action.setData("favorite")

        # v3.0 星标
        star_label = "取消星标" if item.is_starred else "星标"
        star_action = menu.addAction(star_label)
        star_action.setData("star")

        # 置顶
        pin_label = "取消置顶" if item.is_pinned else "置顶"
        pin_action = menu.addAction(pin_label)
        pin_action.setData("pin")

        # 删除
        menu.addSeparator()
        del_action = menu.addAction("删除")
        del_action.setData("delete")

        # 标签子菜单
        current_tag_ids = {t.id for t in item.tags if t.id is not None}
        addable = [t for t in self._all_tags if t.id not in current_tag_ids]

        if addable or item.tags:
            menu.addSeparator()
            if addable:
                add_menu = menu.addMenu("添加标签")
                for tag in addable:
                    action = add_menu.addAction(tag.name)
                    action.setData(("add", tag.id))
            if item.tags:
                remove_menu = menu.addMenu("移除标签")
                for tag in item.tags:
                    action = remove_menu.addAction(tag.name)
                    action.setData(("remove", tag.id))

        menu.addSeparator()

        # 多选模式
        multi_action = menu.addAction("多选模式")
        multi_action.setData("multi_select")

        pos = event.globalPos() if hasattr(event, "globalPos") else event.globalPosition().toPoint()
        result = menu.exec(pos)
        if not result or not result.data():
            return

        data = result.data()
        if isinstance(data, tuple):
            # 标签操作
            action_type, tag_id = data
            if action_type == "add":
                self.tag_add_requested.emit(item.id, tag_id)
            elif action_type == "remove":
                self.tag_remove_requested.emit(item.id, tag_id)
        elif data == "copy":
            self.item_clicked.emit(item)
        elif data == "preview":
            self.preview_requested.emit(item)
        elif data == "favorite":
            self.favorite_toggled.emit(item.id)
        elif data == "star":
            self.star_toggled.emit(item.id)
        elif data == "pin":
            self.pin_clicked.emit(item.id)
        elif data == "delete":
            self.delete_clicked.emit(item.id)
        elif data == "multi_select":
            self.multi_select_toggled.emit()
