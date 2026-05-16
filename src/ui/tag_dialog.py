"""Dialog for creating, editing, and deleting tags."""
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


class _TagRowWidget(QWidget):
    """Widget for a single tag row inside the list."""

    edit_requested = pyqtSignal(int)   # tag_id
    delete_requested = pyqtSignal(int)  # tag_id

    def __init__(self, tag: Tag, parent=None):
        super().__init__(parent)
        self.tag = tag
        assert tag.id is not None, "TagRowWidget requires a persisted tag with an id"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        # Color dot
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet(
            f"background: {tag.color}; border-radius: 7px;"
        )
        layout.addWidget(dot)

        # Tag name
        name_label = QLabel(tag.name)
        name_label.setStyleSheet("color: white; font-size: 13px;")
        layout.addWidget(name_label, 1)

        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedWidth(50)
        edit_btn.setStyleSheet(
            "QPushButton { color: #4A90D9; background: none; border: none; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        tag_id = tag.id
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(tag_id))
        layout.addWidget(edit_btn)

        # Delete button
        del_btn = QPushButton("Delete")
        del_btn.setFixedWidth(60)
        del_btn.setStyleSheet(
            "QPushButton { color: #ff6b6b; background: none; border: none; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        del_btn.clicked.connect(lambda: self.delete_requested.emit(tag_id))
        layout.addWidget(del_btn)


class TagDialog(QDialog):
    """Dialog for managing all tags."""

    tags_changed = pyqtSignal()

    def __init__(self, api_client: ApiClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._selected_color = "#4A90D9"
        self._tags: list[Tag] = []
        self._setup_ui()
        self._reload_tags()

    # ── UI setup ──

    def _setup_ui(self) -> None:
        self.setWindowTitle("Manage Tags")
        self.setFixedSize(420, 480)
        self.setStyleSheet(
            "QDialog { background: #2b2b2b; }"
            "QLabel { color: white; }"
            "QLineEdit {"
            "  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);"
            "  border-radius: 6px; padding: 6px 10px; color: white; font-size: 13px;"
            "}"
        )

        root = QVBoxLayout(self)

        # ── Top row: name input + color picker + add button ──
        top = QHBoxLayout()

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Tag name...")
        self._name_input.setMaxLength(20)
        top.addWidget(self._name_input, 1)

        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(30, 30)
        self._update_color_btn()
        self._color_btn.clicked.connect(self._pick_color)
        top.addWidget(self._color_btn)

        add_btn = QPushButton("Add")
        add_btn.setFixedWidth(60)
        add_btn.setStyleSheet(
            "QPushButton { background: #4A90D9; color: white; border-radius: 6px;"
            "  padding: 6px; font-size: 13px; }"
            "QPushButton:hover { background: #5aa0e9; }"
        )
        add_btn.clicked.connect(self._on_add)
        top.addWidget(add_btn)

        root.addLayout(top)

        # ── Tag list ──
        self._list_widget = QListWidget()
        self._list_widget.setStyleSheet(
            "QListWidget { background: #333; border: 1px solid #444; border-radius: 8px; }"
            "QListWidget::item { padding: 0; }"
            "QListWidget::item:selected { background: rgba(74,144,217,0.3); }"
        )
        root.addWidget(self._list_widget, 1)

        # ── Close button ──
        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        root.addLayout(bottom)

    # ── Tag list management ──

    def _reload_tags(self) -> None:
        """Reload all tags into the list widget."""
        self._list_widget.clear()
        self._tags = self.api_client.get_all_tags()
        for tag in self._tags:
            self._add_tag_row(tag)

    def _add_tag_row(self, tag: Tag) -> None:
        """Insert one tag row into the list widget."""
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 38))
        # Store tag id on item for later lookup
        item.setData(Qt.ItemDataRole.UserRole, tag.id)

        widget = _TagRowWidget(tag)
        widget.edit_requested.connect(self._on_edit)
        widget.delete_requested.connect(self._on_delete)

        self._list_widget.addItem(item)
        self._list_widget.setItemWidget(item, widget)

    # ── Actions ──

    def _on_add(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入标签名称")
            return
        if len(self._tags) >= 100:
            QMessageBox.warning(self, "提示", "标签数量已达上限")
            return
        if any(t.name == name for t in self._tags):
            QMessageBox.warning(self, "提示", "已存在同名标签")
            return
        try:
            self.api_client.create_tag(name, self._selected_color)
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        self._name_input.clear()
        self._reload_tags()
        self.tags_changed.emit()

    def _on_edit(self, tag_id: int) -> None:
        """Edit a tag: prompt for new name and color."""
        tags = self.api_client.get_all_tags()
        tag = next((t for t in tags if t.id == tag_id), None)
        if tag is None:
            return

        # Simple inline approach: use input dialogs
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "Edit Tag", "Tag name:", text=tag.name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            return

        color = QColorDialog.getColor(QColor(tag.color), self, "Tag color")
        if not color.isValid():
            color = QColor(tag.color)

        try:
            self.api_client.update_tag(tag_id, new_name, color.name())
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return

        self._reload_tags()
        self.tags_changed.emit()

    def _on_delete(self, tag_id: int) -> None:
        """Delete a tag after confirmation."""
        tags = self.api_client.get_all_tags()
        tag = next((t for t in tags if t.id == tag_id), None)
        if tag is None:
            return

        reply = QMessageBox.question(
            self,
            "Delete Tag",
            f"Delete tag '{tag.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.api_client.delete_tag(tag_id)
            self._reload_tags()
            self.tags_changed.emit()

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._selected_color), self, "Tag color")
        if color.isValid():
            self._selected_color = color.name()
            self._update_color_btn()

    def _update_color_btn(self) -> None:
        self._color_btn.setStyleSheet(
            f"QPushButton {{ background: {self._selected_color};"
            f"  border-radius: 6px; border: 1px solid #666; }}"
        )
