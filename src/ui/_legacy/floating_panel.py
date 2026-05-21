"""Floating panel UI - the main clipboard station window."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPoint, Qt, QTimer, QUrl, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent, QKeyEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.api_client import ApiClient
from src.models.clipboard_item import ClipboardItem
from src.ui.clipboard_list_model import ClipboardListModel
from src.ui.clipboard_item_delegate import ClipboardItemDelegate
from src.ui.design_system import Palette, Fonts, Spacing, Radius, Sizes
from src.ui.tag_chip import TagChip
from src.ui.tag_dialog import TagDialog

logger = logging.getLogger("eleven.ui")


def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'R,G,B' string for use in rgba()."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"

PANEL_STYLE = f"""
QListView {{
    background: {Palette.BG_PRIMARY};
    border: none;
    outline: none;
}}
QListView::item {{
    padding: {Spacing.XS}px;
    border: none;
}}
QListView::item:selected {{
    background: {Palette.BG_ACTIVE};
}}
QLineEdit {{
    background: {Palette.BG_PRIMARY};
    border: 1px solid {Palette.BORDER};
    border-radius: {Radius.MD}px;
    padding: {Spacing.SM}px {Spacing.MD}px;
    color: {Palette.TEXT_PRIMARY};
    font-family: {Fonts.FAMILY_PRIMARY};
    font-size: {Fonts.SIZE_LG}px;
}}
QLineEdit:focus {{
    border-color: {Palette.TEXT_PRIMARY};
}}
QPushButton[group="tab"] {{
    background: {Palette.BG_SECONDARY};
    border: none;
    border-radius: {Radius.SM}px;
    padding: {Spacing.XS}px {Spacing.SM}px;
    color: {Palette.TEXT_SECONDARY};
    font-size: {Fonts.SIZE_SM}px;
}}
QPushButton[group="tab"]:checked {{
    background: {Palette.TEXT_PRIMARY};
    color: {Palette.BG_PRIMARY};
}}
"""


class FloatingPanel(QWidget):
    """The main floating clipboard panel."""

    send_to_preview = pyqtSignal(list)  # v4.0: send selected items to preview bar
    preview_bar_toggle = pyqtSignal()   # v4.1: toggle preview bar visibility

    def __init__(self, api_client: ApiClient):
        super().__init__()
        self.api_client = api_client
        self._current_group_id: Optional[int] = None  # kept for API compat, no longer exposed in UI
        self._group_buttons: list[QPushButton] = []  # deprecated, kept for compat
        self._current_category: Optional[str] = None
        self._category_buttons: list[QPushButton] = []
        self._current_project: str = "all"
        self._project_buttons: list[QPushButton] = []
        self._active_tag_ids: set[int] = set()
        self._tag_chips: list[TagChip] = []
        self._drag_pos: Optional[QPoint] = None
        # 多选模式
        self._multi_select_mode: bool = False
        self._selected_item_ids: set[int] = set()
        # 预览窗口
        self._preview_windows: list = []
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._load_categories()
        self._load_project_combo()
        self._load_tags()

    def _setup_window(self) -> None:
        self.setWindowTitle("拾遗")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        # 使用相对尺寸，适配高 DPI
        screen = QApplication.primaryScreen()
        if screen:
            dpi = screen.logicalDotsPerInch()
            scale = dpi / 96.0
            self.setFixedSize(int(380 * scale), int(520 * scale))
        else:
            self.setFixedSize(380, 520)
        self.setStyleSheet(PANEL_STYLE)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题栏 — 可拖拽区域
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(52)
        self._title_bar.setCursor(Qt.CursorShape.SizeAllCursor)
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        # 状态点 (8px)
        self._status_dot = QLabel()
        self._status_dot.setFixedSize(8, 8)
        self._status_dot.setStyleSheet(f"background: {Palette.STATUS_OFFLINE}; border-radius: 4px; margin-left: {Spacing.XS}px;")
        title_layout.addWidget(self._status_dot)

        self._capacity_label = QLabel()
        self._capacity_label.setStyleSheet(f"color: {Palette.TEXT_TERTIARY}; font-size: {Fonts.SIZE_MD}px;")
        title_layout.addWidget(self._capacity_label)

        title_layout.addStretch()

        self._merge_btn = QPushButton("合并")
        self._merge_btn.setStyleSheet(f"color: {Palette.TEXT_PRIMARY}; background: none; border: none; font-weight: {Fonts.WEIGHT_MEDIUM};")
        self._merge_btn.clicked.connect(self._on_merge)
        self._merge_btn.setVisible(False)
        title_layout.addWidget(self._merge_btn)

        self._to_preview_btn = QPushButton("预览栏")
        self._to_preview_btn.setStyleSheet(
            f"QPushButton {{ color: {Palette.TEXT_PRIMARY}; background: none; border: none; "
            f"font-size: {Fonts.SIZE_MD}px; padding: {Spacing.XS}px {Spacing.SM}px; font-weight: {Fonts.WEIGHT_MEDIUM}; }}"
            f"QPushButton:hover {{ background: {Palette.BG_HOVER}; border-radius: {Radius.SM}px; }}"
        )
        self._to_preview_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._to_preview_btn.clicked.connect(self._on_preview_bar_toggle)
        title_layout.addWidget(self._to_preview_btn)

        self._select_btn = QPushButton("多选")
        self._select_btn.setStyleSheet(
            f"QPushButton {{ color: {Palette.TEXT_PRIMARY}; background: none; border: none; "
            f"font-size: {Fonts.SIZE_MD}px; padding: {Spacing.XS}px {Spacing.SM}px; font-weight: {Fonts.WEIGHT_MEDIUM}; }}"
            f"QPushButton:hover {{ background: {Palette.BG_HOVER}; border-radius: {Radius.SM}px; }}"
        )
        self._select_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._select_btn.setCheckable(True)
        self._select_btn.clicked.connect(self._toggle_multi_select_from_btn)
        title_layout.addWidget(self._select_btn)

        self._export_btn_title = QPushButton("导出")
        self._export_btn_title.setStyleSheet(
            f"QPushButton {{ color: {Palette.TEXT_PRIMARY}; background: none; border: none; "
            f"font-size: {Fonts.SIZE_MD}px; padding: {Spacing.XS}px {Spacing.SM}px; font-weight: {Fonts.WEIGHT_MEDIUM}; }}"
            f"QPushButton:hover {{ background: {Palette.BG_HOVER}; border-radius: {Radius.SM}px; }}"
        )
        self._export_btn_title.setCursor(Qt.CursorShape.ArrowCursor)
        self._export_btn_title.clicked.connect(self._on_export_from_title)
        title_layout.addWidget(self._export_btn_title)

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(
            f"QPushButton {{ color: {Palette.STATUS_ERROR}; background: none; border: none; }}"
            f"QPushButton:hover {{ background: rgba({_hex_to_rgb(Palette.STATUS_ERROR)},0.1); border-radius: {Radius.SM}px; }}"
        )
        clear_btn.setCursor(Qt.CursorShape.ArrowCursor)
        clear_btn.clicked.connect(self._on_clear)
        title_layout.addWidget(clear_btn)
        layout.addWidget(self._title_bar)

        # v3.0 拖拽覆盖层（初始隐藏）
        self._drop_overlay = QLabel("📥 释放文件以收录到拾遗", self)
        self._drop_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_overlay.setStyleSheet(
            "background: rgba(176, 141, 87, 0.15);"
            "border: 2px dashed #B08D57; border-radius: 8px;"
            "color: #B08D57; font-size: 14px;"
        )
        self._drop_overlay.setVisible(False)
        self.setAcceptDrops(True)

        # 筛选器行：[项目 ▾] [来源 ▾]
        self._filter_bar = QHBoxLayout()
        self._filter_bar.setSpacing(8)
        self._filter_bar.setContentsMargins(0, 0, 0, 0)

        # 项目下拉
        proj_label = QLabel("项目")
        proj_label.setStyleSheet(f"color: {Palette.TEXT_TERTIARY}; font-size: {Fonts.SIZE_SM}px;")
        self._filter_bar.addWidget(proj_label)
        self._project_combo = QComboBox()
        self._project_combo.setStyleSheet(
            f"QComboBox {{ background: {Palette.BG_SECONDARY}; color: {Palette.TEXT_PRIMARY}; border: none;"
            f" border-radius: {Radius.SM}px; padding: {Spacing.XS}px {Spacing.SM}px; font-size: {Fonts.SIZE_SM}px; min-width: 80px; }}"
            "QComboBox::drop-down { border: none; }"
            f"QComboBox QAbstractItemView {{ background: {Palette.BG_PRIMARY}; color: {Palette.TEXT_PRIMARY};"
            f" selection-background-color: rgba({_hex_to_rgb(Palette.ACCENT_GOLD)},0.25); }}"
        )
        self._project_combo.currentTextChanged.connect(self._on_project_changed)
        self._filter_bar.addWidget(self._project_combo)

        # 项目加号按钮
        self._add_project_btn = QPushButton("+")
        self._add_project_btn.setFixedSize(24, 24)
        self._add_project_btn.setStyleSheet(
            f"QPushButton {{ background: {Palette.ACCENT_GOLD}; color: #fff; border: none;"
            f" border-radius: 12px; font-size: {Fonts.SIZE_LG}px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {Palette.ACCENT_GOLD_LIGHT}; }}"
        )
        self._add_project_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_project_btn.clicked.connect(self._on_create_project)
        self._filter_bar.addWidget(self._add_project_btn)

        self._filter_bar.addStretch()
        layout.addLayout(self._filter_bar)

        # 分类标签栏
        self._category_bar = QHBoxLayout()
        self._category_bar.setSpacing(4)
        layout.addLayout(self._category_bar)

        # 标签过滤栏
        self._tag_bar_scroll = QScrollArea()
        self._tag_bar_scroll.setWidgetResizable(True)
        self._tag_bar_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._tag_bar_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._tag_bar_scroll.setFixedHeight(30)
        self._tag_bar_scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
        )
        tag_bar_container = QWidget()
        tag_bar_container.setStyleSheet(f"background: transparent;")
        self._tag_bar = QHBoxLayout(tag_bar_container)
        self._tag_bar.setContentsMargins(0, 0, 0, 0)
        self._tag_bar.setSpacing(Spacing.XS)
        self._tag_bar_scroll.setWidget(tag_bar_container)
        layout.addWidget(self._tag_bar_scroll)

        # 搜索框 (带清除按钮和 300ms 防抖)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)

        search_container = QWidget()
        search_container.setStyleSheet("background: transparent;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索剪贴内容...")
        self.search_box.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_box)

        self._search_clear_btn = QPushButton("✕", search_container)
        self._search_clear_btn.setFixedSize(24, 24)
        self._search_clear_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._search_clear_btn.setStyleSheet(
            f"QPushButton {{ color: {Palette.TEXT_TERTIARY}; background: none; border: none; font-size: {Fonts.SIZE_MD}px; }}"
            f"QPushButton:hover {{ color: {Palette.TEXT_PRIMARY}; }}"
        )
        self._search_clear_btn.clicked.connect(self._clear_search)
        self._search_clear_btn.setVisible(False)
        search_layout.addWidget(self._search_clear_btn)

        layout.addWidget(search_container)

        # 多选操作栏（默认隐藏）
        self._action_bar = QWidget()
        self._action_bar.setVisible(False)
        action_layout = QHBoxLayout(self._action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(Spacing.XS)

        self._selection_label = QLabel("已选 0 项")
        self._selection_label.setStyleSheet(f"color: {Palette.TEXT_SECONDARY}; font-size: {Fonts.SIZE_SM}px;")
        action_layout.addWidget(self._selection_label)

        action_layout.addStretch()

        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet(f"color: {Palette.TEXT_SECONDARY}; background: none; border: none; font-size: {Fonts.SIZE_SM}px;")
        select_all_btn.clicked.connect(self._on_select_all)
        action_layout.addWidget(select_all_btn)

        export_btn = QPushButton("导出")
        export_btn.setStyleSheet(f"color: {Palette.ACCENT_GOLD}; background: none; border: none; font-size: {Fonts.SIZE_SM}px;")
        export_btn.clicked.connect(self._on_export_selected)
        action_layout.addWidget(export_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet(f"color: {Palette.STATUS_ERROR}; background: none; border: none; font-size: {Fonts.SIZE_SM}px;")
        delete_btn.clicked.connect(self._on_batch_delete)
        action_layout.addWidget(delete_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(f"color: {Palette.TEXT_TERTIARY}; background: none; border: none; font-size: {Fonts.SIZE_SM}px;")
        cancel_btn.clicked.connect(self._exit_multi_select)
        action_layout.addWidget(cancel_btn)

        layout.addWidget(self._action_bar)

        # 列表
        self.list_view = QListView()
        self.list_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.list_view.setSelectionMode(QListView.SelectionMode.MultiSelection)

        # 设置模型和委托
        self._model = ClipboardListModel()
        self._delegate = ClipboardItemDelegate()
        self.list_view.setModel(self._model)
        self.list_view.setItemDelegate(self._delegate)

        self.list_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._delegate.item_clicked.connect(self._on_item_clicked)
        self._delegate.delete_clicked.connect(self._on_item_deleted)
        self._delegate.pin_clicked.connect(self.api_client.toggle_pin)
        self._delegate.tag_add_requested.connect(self._on_tag_add)
        self._delegate.tag_remove_requested.connect(self._on_tag_remove)
        self._delegate.preview_requested.connect(self._on_preview_requested)
        self._delegate.export_requested.connect(self._on_export_items)
        self._delegate.favorite_toggled.connect(self._on_favorite_toggled)
        self._delegate.star_toggled.connect(self._on_star_toggled)
        self._delegate.multi_select_toggled.connect(self._on_multi_select_toggled)
        self._delegate.selection_toggled.connect(self._on_item_selection_toggled)

        layout.addWidget(self.list_view, 1)

        # 空态提示（覆盖在列表上方）
        self._empty_label = QLabel("还没有收录内容\n\n拖入文件 / 按 Ctrl+V 收录", self)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {Palette.TEXT_TERTIARY}; font-size: {Fonts.SIZE_XL}px; background: transparent;"
        )
        self._empty_label.setVisible(False)

    def _connect_signals(self) -> None:
        self.api_client.items_changed.connect(self.refresh_list)

    def _load_tags(self) -> None:
        for chip in self._tag_chips:
            chip.deleteLater()
        self._tag_chips.clear()
        while self._tag_bar.count():
            child = self._tag_bar.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        tags = self.api_client.get_all_tags()
        self._delegate.set_all_tags(tags)
        for tag in tags:
            chip = TagChip(tag.id, tag.name, tag.color)
            if tag.id in self._active_tag_ids:
                chip.setChecked(True)
            chip.tag_clicked.connect(self._on_tag_toggled)
            self._tag_bar.addWidget(chip)
            self._tag_chips.append(chip)

        tag_label = QLabel("标签")
        tag_label.setStyleSheet(f"color: {Palette.TEXT_TERTIARY}; font-size: {Fonts.SIZE_MD}px; margin-right: {Spacing.XS}px;")
        self._tag_bar.addWidget(tag_label)

        add_tag_btn = QPushButton("+")
        add_tag_btn.setFixedSize(24, 24)
        add_tag_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(255,255,255,0.08); color: {Palette.TEXT_SECONDARY};"
            f"  border: 1px dashed #4A4A4A; border-radius: 50%; font-size: {Fonts.SIZE_LG}px; }}"
            f"QPushButton:hover {{ color: {Palette.TEXT_PRIMARY}; border-color: {Palette.ACCENT_GOLD}; }}"
        )
        add_tag_btn.clicked.connect(self._open_tag_dialog)
        self._tag_bar.addWidget(add_tag_btn)
        self._tag_bar.addStretch()

    def _load_categories(self) -> None:
        for btn in self._category_buttons:
            btn.deleteLater()
        self._category_buttons.clear()

        categories = [
            (None, "全部", "#888888"),
            ("DEFAULT", "文本", "#4A90D9"),
            ("IMAGE", "图片", "#3A8B40"),
            ("WORD", "Word", "#5B8DEF"),
            ("EXCEL", "Excel", "#3A8B40"),
            ("PDF", "PDF", "#C94043"),
            ("PPT", "PPT", "#C4934A"),
            ("ARCHIVE", "压缩", "#C4934A"),
        ]
        for cat_key, cat_label, cat_color in categories:
            btn = QPushButton(cat_label)
            btn.setProperty("group", "tab")
            btn.setProperty("cat_key", cat_key)
            btn.setProperty("cat_color", cat_color)
            btn.setCheckable(True)
            btn.setChecked(cat_key is None)
            btn.clicked.connect(
                lambda checked, k=cat_key: self._on_category_clicked(k)
            )
            self._apply_category_style(btn, cat_key is None, cat_color)
            self._category_bar.addWidget(btn)
            self._category_buttons.append(btn)
        self._category_bar.addStretch()

    def _apply_category_style(self, btn, is_checked: bool, color: str):
        if is_checked:
            btn.setStyleSheet(
                f"QPushButton {{ background: {color}; color: white; border: none;"
                f" border-radius: 6px; padding: 4px 8px; font-size: 11px; }}"
            )
        else:
            btn.setStyleSheet(
                f"QPushButton {{ background: #2A2A2A; color: #888; border: none;"
                f" border-radius: 6px; padding: 4px 8px; font-size: 11px; }}"
                f"QPushButton:hover {{ background: rgba({_hex_to_rgb(color)},0.15); }}"
            )

    def _load_project_combo(self) -> None:
        self._project_combo.blockSignals(True)
        self._project_combo.clear()
        self._project_combo.addItem("全部")
        self._project_combo.addItem("📁 默认", "default")
        try:
            projects = self.api_client.get_projects()
            for proj in projects:
                name = proj.get("name", "")
                if name == "default":
                    continue
                icon = proj.get("icon", "📁")
                self._project_combo.addItem(f"{icon} {name}", name)
        except Exception:
            logger.error("Failed to load projects", exc_info=True)
        self._project_combo.setCurrentIndex(0)
        self._project_combo.blockSignals(False)

    def _on_project_changed(self, text: str) -> None:
        data = self._project_combo.currentData()
        self._current_project = data if data else "all"
        self.refresh_list()

    def _on_create_project(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "创建项目", "项目名称:")
        if ok and name.strip():
            try:
                self.api_client.create_project(name.strip())
                self._load_project_combo()
                self.refresh_list()
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "创建失败", str(e))

    def _show_project_context_menu(self, global_pos, project_id: int, name: str):
        from PyQt6.QtWidgets import QMenu, QInputDialog, QColorDialog, QMessageBox
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background: {Palette.BG_SECONDARY}; border: 1px solid {Palette.BORDER};"
            f" color: {Palette.TEXT_PRIMARY}; padding: {Spacing.XS}px; border-radius: {Radius.XL}px; }}"
            f"QMenu::item {{ padding: {Spacing.SM}px {Spacing.XL}px; border-radius: {Radius.SM}px; }}"
            f"QMenu::item:selected {{ background: rgba({_hex_to_rgb(Palette.ACCENT_GOLD)},0.2); }}"
        )
        menu.addAction("重命名").triggered.connect(lambda: self._rename_project(project_id, name))
        menu.addAction("修改颜色").triggered.connect(lambda: self._recolor_project(project_id, name))
        menu.addSeparator()
        menu.addAction("删除").triggered.connect(lambda: self._delete_project(project_id, name))
        menu.exec(self.mapToGlobal(global_pos))

    def _rename_project(self, project_id: int, old_name: str):
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        new_name, ok = QInputDialog.getText(self, "重命名项目", "新名称:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            try:
                # API doesn't have update, so delete + create
                self.api_client.delete_project(project_id)
                self.api_client.create_project(new_name.strip())
                if self._current_project == old_name:
                    self._current_project = new_name.strip()
                self._load_project_combo()
                self.refresh_list()
            except Exception:
                QMessageBox.warning(self, "重命名失败", "请重试")

    def _recolor_project(self, project_id: int, name: str):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(parent=self, title="选择项目颜色")
        if color.isValid():
            # Color is stored in project metadata; for now just reload
            self._load_project_combo()

    def _delete_project(self, project_id: int, name: str) -> None:
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "删除项目",
            f"确定删除项目「{name}」？\n（项目中的条目不会被删除）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_project(project_id)
                if self._current_project == name:
                    self._current_project = "all"
                self._load_project_combo()
                self.refresh_list()
            except Exception:
                logger.error("Failed to delete project", exc_info=True)

    def _on_category_clicked(self, category: Optional[str]) -> None:
        self._current_category = category
        for btn in self._category_buttons:
            is_match = btn.property("cat_key") == category
            btn.setChecked(is_match)
            self._apply_category_style(btn, is_match, btn.property("cat_color") or "#AAAAAA")
        self.refresh_list()

    def _on_tag_toggled(self, tag_id: int, is_selected: bool) -> None:
        if is_selected:
            self._active_tag_ids.add(tag_id)
        else:
            self._active_tag_ids.discard(tag_id)
        self.refresh_list()

    def _open_tag_dialog(self) -> None:
        dialog = TagDialog(self.api_client, self)
        dialog.tags_changed.connect(self._on_tags_changed)
        dialog.exec()

    def _on_tags_changed(self) -> None:
        self._load_tags()
        self.refresh_list()

    def _on_tag_add(self, item_id: int, tag_id: int) -> None:
        try:
            self.api_client.add_tag_to_item(item_id, tag_id)
        except ValueError:
            pass

    def _on_tag_remove(self, item_id: int, tag_id: int) -> None:
        self.api_client.remove_tag_from_item(item_id, tag_id)

    def _on_group_clicked(self, group_id: Optional[int]) -> None:
        self._current_group_id = group_id
        self.refresh_list()

    def update_status(self, status: str) -> None:
        """Update the status dot color in the title bar."""
        colors = {
            "online": "#4CAF50", "warning": "#FF9800",
            "error": "#F44336", "offline": "#757575",
        }
        color = colors.get(status, "#757575")
        self._status_dot.setStyleSheet(f"background: {color}; border-radius: 4px;")

    def refresh_list(self) -> None:
        """Reload all items from manager, applying tag/group/category/project filters."""
        self._model.clear()
        query = self.search_box.text().strip() or None
        tag_ids = list(self._active_tag_ids) if self._active_tag_ids else None
        project = self._current_project if self._current_project != "all" else None
        try:
            items = self.api_client.search_with_filters(
                query=query,
                tag_ids=tag_ids,
                group_id=self._current_group_id,
                category=self._current_category,
                project=project,
                limit=200,
            )
            self._model.set_items(items)
            self.list_view.viewport().update()
            self._update_empty_state(items, query)
        except Exception:
            logger.error("refresh_list failed", exc_info=True)

        self._update_capacity()

    def _update_empty_state(self, items: list, query: str | None) -> None:
        """Show/hide empty state overlay."""
        if items:
            self._empty_label.setVisible(False)
            return
        has_filters = (
            query or self._active_tag_ids or self._current_group_id
            or self._current_category or self._current_project != "all"
        )
        if has_filters:
            if query:
                self._empty_label.setText(f"没有找到包含「{query}」的内容")
            else:
                self._empty_label.setText("没有找到匹配内容")
        else:
            self._empty_label.setText("还没有收录内容\n\n拖入文件 / 按 Ctrl+V 收录")
        self._empty_label.setVisible(True)

    def _on_item_clicked(self, item: ClipboardItem) -> None:
        """点击条目：复制到剪贴板（不关闭面板）。"""
        self.api_client.copy_item(item.id)

    def _on_search_text_changed(self, text: str) -> None:
        self._search_clear_btn.setVisible(bool(text))
        self._search_timer.start()

    def _do_search(self) -> None:
        self.refresh_list()

    def _clear_search(self) -> None:
        self.search_box.clear()
        self.search_box.setFocus()

    def _on_clear(self) -> None:
        self.api_client.clear_all()
        self._model.clear()

    def _update_capacity(self) -> None:
        count = self.api_client.get_count()
        max_items = self.api_client.get_max_items()
        self._capacity_label.setText(f"({count}/{max_items})")
        if count >= max_items * 0.9:
            self._capacity_label.setStyleSheet("color: #C94043; font-size: 12px;")
        else:
            self._capacity_label.setStyleSheet("color: #666; font-size: 12px;")

    def _on_selection_changed(self) -> None:
        selected = self.list_view.selectionModel().selectedIndexes()
        count = len(selected)
        self._merge_btn.setVisible(count >= 2)

    def _on_merge(self) -> None:
        selected = self.list_view.selectionModel().selectedIndexes()
        if len(selected) < 2:
            return
        item_ids = []
        for index in selected:
            item = self._model.get_item(index)
            if item and item.id:
                item_ids.append(item.id)
        if len(item_ids) >= 2:
            self.api_client.merge_items(item_ids)

    def _on_send_to_preview(self) -> None:
        """Send selected items to preview bar."""
        selected = self.list_view.selectionModel().selectedIndexes()
        items = []
        for index in selected:
            item = self._model.get_item(index)
            if isinstance(item, ClipboardItem):
                items.append(item)
        if items:
            self.send_to_preview.emit(items)
            self.hide()

    def _on_preview_bar_toggle(self) -> None:
        """Toggle preview bar: send selected items if any, otherwise just toggle visibility."""
        selected = self.list_view.selectionModel().selectedIndexes()
        if selected:
            self._on_send_to_preview()
        else:
            self.preview_bar_toggle.emit()

    # ── 多选模式 ──

    def _on_multi_select_toggled(self) -> None:
        self._multi_select_mode = not self._multi_select_mode
        if not self._multi_select_mode:
            self._selected_item_ids.clear()
        self._action_bar.setVisible(self._multi_select_mode)
        self._delegate.set_multi_select(self._multi_select_mode, self._selected_item_ids)
        self._update_selection_label()
        self._update_select_btn_state()
        self.list_view.viewport().update()

    def _toggle_multi_select_from_btn(self, checked: bool) -> None:
        """标题栏多选按钮点击处理."""
        self._multi_select_mode = checked
        if not checked:
            self._selected_item_ids.clear()
        self._action_bar.setVisible(checked)
        self._delegate.set_multi_select(checked, self._selected_item_ids)
        self._update_selection_label()
        self._update_select_btn_state()
        self.list_view.viewport().update()

    def _update_select_btn_state(self) -> None:
        """同步标题栏多选按钮的显示状态."""
        self._select_btn.blockSignals(True)
        self._select_btn.setChecked(self._multi_select_mode)
        self._select_btn.setText("取消多选" if self._multi_select_mode else "多选")
        if self._multi_select_mode:
            self._select_btn.setStyleSheet(
                f"QPushButton {{ color: #fff; background: rgba({_hex_to_rgb(Palette.ACCENT_GOLD)},0.3);"
                f" border: none; font-size: {Fonts.SIZE_MD}px; padding: {Spacing.XS}px {Spacing.SM}px; border-radius: {Radius.SM}px; }}"
            )
        else:
            self._select_btn.setStyleSheet(
                f"QPushButton {{ color: {Palette.ACCENT_GOLD}; background: none; border: none;"
                f" font-size: {Fonts.SIZE_MD}px; padding: {Spacing.XS}px {Spacing.SM}px; }}"
                f"QPushButton:hover {{ background: rgba({_hex_to_rgb(Palette.ACCENT_GOLD)},0.15); border-radius: {Radius.SM}px; }}"
            )
        self._select_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._select_btn.blockSignals(False)

    def _on_export_from_title(self) -> None:
        """标题栏导出按钮：导出当前选中项，无选中则提示."""
        if not self._selected_item_ids:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "导出",
                "请先选择要导出的条目\n（点击「多选」按钮可选择多个）",
            )
            return
        items = []
        for i in range(self._model.rowCount()):
            index = self._model.index(i)
            item = self._model.get_item(index)
            if item and item.id in self._selected_item_ids:
                items.append(item)
        if items:
            self._on_export_items(items)

    def _on_item_selection_toggled(self, item_id: int) -> None:
        if item_id in self._selected_item_ids:
            self._selected_item_ids.discard(item_id)
        else:
            self._selected_item_ids.add(item_id)
        self._delegate.set_multi_select(self._multi_select_mode, self._selected_item_ids)
        self._update_selection_label()
        self.list_view.viewport().update()

    def _on_select_all(self) -> None:
        for i in range(self._model.rowCount()):
            index = self._model.index(i)
            item = self._model.get_item(index)
            if item and item.id:
                self._selected_item_ids.add(item.id)
        self._delegate.set_multi_select(self._multi_select_mode, self._selected_item_ids)
        self._update_selection_label()
        self.list_view.viewport().update()

    def _exit_multi_select(self) -> None:
        self._multi_select_mode = False
        self._selected_item_ids.clear()
        self._action_bar.setVisible(False)
        self._delegate.set_multi_select(False, set())
        self._update_select_btn_state()
        self.list_view.viewport().update()

    def _update_selection_label(self) -> None:
        self._selection_label.setText(f"已选 {len(self._selected_item_ids)} 项")

    # ── 收藏/删除/导出 ──

    def _on_item_deleted(self, item_id: int) -> None:
        self.api_client.delete_item(item_id)
        self.refresh_list()

    def _on_favorite_toggled(self, item_id: int) -> None:
        self.api_client.toggle_favorite(item_id)
        self.refresh_list()

    def _on_star_toggled(self, item_id: int) -> None:
        self.api_client.toggle_star(item_id)
        self.refresh_list()

    def _on_batch_delete(self) -> None:
        if not self._selected_item_ids:
            return
        ids = list(self._selected_item_ids)
        self.api_client.batch_delete(ids)
        self._exit_multi_select()
        self.refresh_list()

    def _on_export_selected(self) -> None:
        if not self._selected_item_ids:
            return
        items = []
        for i in range(self._model.rowCount()):
            index = self._model.index(i)
            item = self._model.get_item(index)
            if item and item.id in self._selected_item_ids:
                items.append(item)
        if items:
            self._on_export_items(items)

    def _on_export_items(self, items: list) -> None:
        from src.ui.export_dialog import ExportDialog
        dlg = ExportDialog(items, self)
        if dlg.exec() == ExportDialog.DialogCode.Accepted:
            if dlg.result_key == ExportDialog.PREVIEW_MODE:
                self.send_to_preview.emit(items)
                self.hide()

    # ── 预览窗口 ──

    def _on_preview_requested(self, item) -> None:
        from src.ui.preview_window import PreviewWindow
        preview = PreviewWindow(item, parent=None)
        preview.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        preview.show()
        self._preview_windows.append(preview)
        # 清理已关闭的窗口
        self._preview_windows = [w for w in self._preview_windows if w.isVisible()]

    def toggle(self) -> None:
        try:
            if self.isVisible() and self.isActiveWindow():
                self._animate_hide()
            elif self.isVisible():
                # Visible but not active — bring to front instead of hiding
                self.raise_()
                self.activateWindow()
                self.search_box.setFocus()
            else:
                self.refresh_list()
                self._center_on_screen()
                self._animate_show()
        except Exception:
            logger.error("Panel toggle failed", exc_info=True)

    def _animate_show(self) -> None:
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_box.setFocus()
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(160)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()
        self._show_anim = anim

    def _animate_hide(self) -> None:
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(120)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self._finish_hide)
        anim.start()
        self._hide_anim = anim

    def _finish_hide(self) -> None:
        self.hide()
        self.setWindowOpacity(1.0)

    def _center_on_screen(self) -> None:
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.width() - self.width() - 40
            y = (geo.height() - self.height()) // 2
            self.move(geo.x() + x, geo.y() + y)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if not event:
            return super().keyPressEvent(event)

        key = event.key()
        mods = event.modifiers()
        ctrl = mods & Qt.KeyboardModifier.ControlModifier
        shift = mods & Qt.KeyboardModifier.ShiftModifier

        # Escape: 清空搜索 → 关闭面板
        if key == Qt.Key.Key_Escape:
            if self.search_box.text():
                self._clear_search()
            else:
                self.hide()
            return

        # Ctrl+V: 粘贴收录
        if key == Qt.Key.Key_V and ctrl:
            self._handle_paste()
            return

        # Ctrl+F: 聚焦搜索框
        if key == Qt.Key.Key_F and ctrl:
            self.search_box.setFocus()
            self.search_box.selectAll()
            return

        # Ctrl+A: 多选模式全选
        if key == Qt.Key.Key_A and ctrl:
            if self._multi_select_mode:
                self._on_select_all()
            return

        # Ctrl+E: 导出
        if key == Qt.Key.Key_E and ctrl:
            self._on_export_from_title()
            return

        # Ctrl+M: 合并
        if key == Qt.Key.Key_M and ctrl:
            self._on_merge()
            return

        # Enter: 复制焦点条目 / Shift+Enter: 预览
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            idx = self.list_view.currentIndex()
            if idx.isValid():
                item = self._model.get_item(idx)
                if item:
                    if shift:
                        self._on_preview_requested(item)
                    else:
                        self.api_client.copy_item(item.id)
            return

        # Delete: 删除选中条目
        if key == Qt.Key.Key_Delete:
            if self._multi_select_mode and self._selected_item_ids:
                self._on_batch_delete()
            else:
                idx = self.list_view.currentIndex()
                if idx.isValid():
                    item = self._model.get_item(idx)
                    if item and item.id:
                        self._on_item_deleted(item.id)
            return

        # ↑/↓: 移动列表焦点
        if key == Qt.Key.Key_Up:
            idx = self.list_view.currentIndex()
            if idx.isValid() and idx.row() > 0:
                new_idx = self._model.index(idx.row() - 1)
                self.list_view.setCurrentIndex(new_idx)
            elif not idx.isValid() and self._model.rowCount() > 0:
                self.list_view.setCurrentIndex(self._model.index(0))
            return
        if key == Qt.Key.Key_Down:
            idx = self.list_view.currentIndex()
            if idx.isValid() and idx.row() < self._model.rowCount() - 1:
                new_idx = self._model.index(idx.row() + 1)
                self.list_view.setCurrentIndex(new_idx)
            elif not idx.isValid() and self._model.rowCount() > 0:
                self.list_view.setCurrentIndex(self._model.index(0))
            return

        super().keyPressEvent(event)

    def _handle_paste(self) -> None:
        """Handle Ctrl+V: read system clipboard and add as new item."""
        paste_fn = getattr(self.api_client, "paste_from_clipboard", None)
        if paste_fn:
            added = paste_fn()
            if added:
                self.refresh_list()
        else:
            # ApiClient 模式：通过 HTTP 接口（暂不支持直接粘贴）
            logger.info("Paste not supported in API client mode")

    def paintEvent(self, event) -> None:
        pass

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)

    # ── v3.0 拖拽收录 ──

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drop_overlay.setVisible(True)
            self._drop_overlay.setGeometry(0, 0, self.width(), self.height())
            self._drop_overlay.raise_()
        else:
            super().dragEnterEvent(event)

    def dragLeaveEvent(self, event) -> None:
        self._drop_overlay.setVisible(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_overlay.setVisible(False)
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_paths.append(url.toLocalFile())
            if file_paths:
                try:
                    self.api_client.import_files(file_paths, source="drag-drop")
                    self.refresh_list()
                except Exception:
                    logger.error("Drop import failed", exc_info=True)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._drop_overlay.setGeometry(0, 0, self.width(), self.height())
        # Position empty label over list area
        if hasattr(self, '_empty_label'):
            self._empty_label.setGeometry(
                self.list_view.x(), self.list_view.y(),
                self.list_view.width(), self.list_view.height()
            )
