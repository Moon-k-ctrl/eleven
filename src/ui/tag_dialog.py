"""Dialog for creating, editing, and deleting tags — ink-wash theme."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.api_client import ApiClient
from src.models.clipboard_item import Tag
from src.ui.theme_styles import (
    DIALOG_STYLE, TAG_COLORS,
    btn_primary, btn_secondary, btn_danger, btn_text,
    ACCENT_MINT, BG_HOVER, BG_TERTIARY, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, BORDER_SOFT,
)


class _TagRowWidget(QWidget):
    """Widget for a single tag row inside the list."""

    edit_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)

    def __init__(self, tag: Tag, parent=None):
        super().__init__(parent)
        self.tag = tag
        assert tag.id is not None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Color dot
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet(f"background: {tag.color}; border-radius: 6px;")
        layout.addWidget(dot)

        # Tag name
        name_label = QLabel(tag.name)
        name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-family: 'Microsoft YaHei';")
        layout.addWidget(name_label, 1)

        # Edit button
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedWidth(50)
        edit_btn.setStyleSheet(btn_text())
        tag_id = tag.id
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(tag_id))
        layout.addWidget(edit_btn)

        # Delete button
        del_btn = QPushButton("删除")
        del_btn.setFixedWidth(50)
        del_btn.setStyleSheet(btn_text().replace(TEXT_TERTIARY, "#F06464"))
        del_btn.clicked.connect(lambda: self.delete_requested.emit(tag_id))
        layout.addWidget(del_btn)


class TagDialog(QDialog):
    """Dialog for managing all tags."""

    tags_changed = pyqtSignal()

    def __init__(self, api_client: ApiClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._selected_color = TAG_COLORS[0]
        self._tags: list[Tag] = []
        self._setup_ui()
        self._reload_tags()

    def _setup_ui(self) -> None:
        self.setWindowTitle("标签管理")
        self.setFixedSize(420, 480)
        self.setStyleSheet(DIALOG_STYLE)

        root = QVBoxLayout(self)
        root.setSpacing(8)

        # Title
        title = QLabel("🏷  标签管理")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold; font-family: 'Microsoft YaHei';")
        root.addWidget(title)

        # Top row: name input + color chips + add button
        top = QHBoxLayout()
        top.setSpacing(8)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("输入标签名称...")
        self._name_input.setMaxLength(20)
        top.addWidget(self._name_input, 1)

        # Color chips (6 presets)
        self._color_chips: list[QPushButton] = []
        for i, color in enumerate(TAG_COLORS[:6]):
            chip = QPushButton()
            chip.setFixedSize(24, 24)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setStyleSheet(self._chip_style(color, color == self._selected_color))
            chip.clicked.connect(lambda _, c=color, idx=i: self._select_color(c, idx))
            self._color_chips.append(chip)
            top.addWidget(chip)

        add_btn = QPushButton("添加")
        add_btn.setFixedWidth(60)
        add_btn.setStyleSheet(btn_primary())
        add_btn.clicked.connect(self._on_add)
        top.addWidget(add_btn)

        root.addLayout(top)

        # Tag list
        self._list_widget = QListWidget()
        self._list_widget.setStyleSheet(
            f"QListWidget {{ background: {BG_TERTIARY}; border: 1px solid {BORDER_SOFT}; border-radius: 8px; padding: 4px; }}"
            f"QListWidget::item {{ padding: 2px; border-radius: 6px; }}"
            f"QListWidget::item:hover {{ background: {BG_HOVER}; }}"
        )
        root.addWidget(self._list_widget, 1)

        # Close button
        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(80)
        close_btn.setStyleSheet(btn_secondary())
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        root.addLayout(bottom)

    def _chip_style(self, color: str, selected: bool) -> str:
        border = f"2px solid {color}" if selected else f"1px solid {BORDER_SOFT}"
        return f"QPushButton {{ background: {color}; border: {border}; border-radius: 12px; }}"

    def _select_color(self, color: str, idx: int) -> None:
        self._selected_color = color
        for i, chip in enumerate(self._color_chips):
            chip.setStyleSheet(self._chip_style(TAG_COLORS[i], i == idx))

    def _reload_tags(self) -> None:
        self._list_widget.clear()
        self._tags = self.api_client.get_all_tags()
        for tag in self._tags:
            self._add_tag_row(tag)

    def _add_tag_row(self, tag: Tag) -> None:
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 38))
        item.setData(Qt.ItemDataRole.UserRole, tag.id)

        widget = _TagRowWidget(tag)
        widget.edit_requested.connect(self._on_edit)
        widget.delete_requested.connect(self._on_delete)

        self._list_widget.addItem(item)
        self._list_widget.setItemWidget(item, widget)

    def _on_add(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            return
        if len(self._tags) >= 100:
            QMessageBox.warning(self, "提示", "标签数量已达上限 (100)")
            return
        if any(t.name == name for t in self._tags):
            QMessageBox.warning(self, "提示", "已存在同名标签")
            return
        try:
            self.api_client.create_tag(name, self._selected_color)
        except ValueError as exc:
            QMessageBox.warning(self, "错误", str(exc))
            return
        self._name_input.clear()
        self._reload_tags()
        self.tags_changed.emit()

    def _on_edit(self, tag_id: int) -> None:
        tags = self.api_client.get_all_tags()
        tag = next((t for t in tags if t.id == tag_id), None)
        if tag is None:
            return

        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "编辑标签", "标签名称:", text=tag.name)
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            return

        color = QColorDialog.getColor(QColor(tag.color), self, "标签颜色")
        if not color.isValid():
            color = QColor(tag.color)

        try:
            self.api_client.update_tag(tag_id, new_name, color.name())
        except ValueError as exc:
            QMessageBox.warning(self, "错误", str(exc))
            return

        self._reload_tags()
        self.tags_changed.emit()

    def _on_delete(self, tag_id: int) -> None:
        tags = self.api_client.get_all_tags()
        tag = next((t for t in tags if t.id == tag_id), None)
        if tag is None:
            return

        reply = QMessageBox.question(
            self, "删除标签", f"确定删除标签「{tag.name}」？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.api_client.delete_tag(tag_id)
            self._reload_tags()
            self.tags_changed.emit()
