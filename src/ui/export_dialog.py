"""Export dialog for batch export of selected clipboard items — ink-wash theme."""
from __future__ import annotations

import os
import shutil
import zipfile

from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout,
    QLabel, QButtonGroup, QPushButton, QRadioButton, QVBoxLayout,
)

from src.models.clipboard_item import ClipboardItem, ContentType
from src.ui.theme_styles import (
    DIALOG_STYLE, btn_primary, btn_secondary,
    TEXT_PRIMARY, TEXT_TERTIARY,
)


class ExportDialog(QDialog):
    """Multi-select export method chooser."""

    PREVIEW_MODE = "preview"

    def __init__(self, items: list[ClipboardItem], parent=None):
        super().__init__(parent)
        self._items = items
        self._result_key: str | None = None
        self.setWindowTitle(f"导出 {len(items)} 项内容")
        self.setFixedSize(420, 320)
        self.setStyleSheet(DIALOG_STYLE)
        self._setup_ui()

    def _detect_default_option(self) -> str:
        """Smart default based on content type composition."""
        has_text = any(i.content_type in (ContentType.TEXT, ContentType.HTML) for i in self._items)
        has_files = any(i.content_type in (ContentType.FILES, ContentType.IMAGE) for i in self._items)
        if has_text and not has_files:
            return "clipboard"
        if has_files and not has_text:
            return "folder"
        return "preview"

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Title
        title = QLabel(f"📤  选择导出方式（共 {len(self._items)} 项）")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; font-family: 'Microsoft YaHei';")
        layout.addWidget(title)

        self._group = QButtonGroup(self)
        default_key = self._detect_default_option()
        options = [
            ("clipboard", "合并写入剪贴板（用分隔线隔开）"),
            ("paths", "复制文件路径到剪贴板"),
            ("folder", "导出到指定文件夹..."),
            ("zip", "打包为 .zip 文件..."),
            ("preview", "发送到预览栏（逐个拖出）"),
        ]
        for i, (key, text) in enumerate(options):
            rb = QRadioButton(text)
            rb.setProperty("export_key", key)
            self._group.addButton(rb, i)
            layout.addWidget(rb)
            if key == default_key:
                rb.setChecked(True)

        layout.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("取消")
        cancel.setStyleSheet(btn_secondary())
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        ok = QPushButton("确定导出")
        ok.setStyleSheet(btn_primary())
        ok.clicked.connect(self._do_export)
        btns.addWidget(ok)
        layout.addLayout(btns)

    @property
    def result_key(self) -> str | None:
        return self._result_key

    def _do_export(self):
        btn = self._group.checkedButton()
        if not btn:
            return
        key = btn.property("export_key")
        self._result_key = key

        if key == "clipboard":
            self._export_clipboard()
        elif key == "paths":
            self._export_paths()
        elif key == "folder":
            if not self._export_folder():
                return
        elif key == "zip":
            if not self._export_zip():
                return
        # "preview" → caller handles via result_key

        self.accept()

    def _export_clipboard(self):
        texts = [i.content_text or "" for i in self._items if i.content_text]
        QApplication.clipboard().setText("\n---\n".join(texts))

    def _export_paths(self):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QMimeData
        paths = []
        for item in self._items:
            if item.file_path:
                paths.append(item.file_path)
            elif item.content_type == ContentType.FILES and item.content_text:
                paths.extend(item.content_text.split("\n"))
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        QApplication.clipboard().setMimeData(mime)

    def _export_folder(self) -> bool:
        folder = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not folder:
            return False
        copied = 0
        for item in self._items:
            if item.file_path and os.path.exists(item.file_path):
                shutil.copy2(item.file_path, folder)
                copied += 1
        self._show_export_done(f"已导出 {copied} 个文件", folder)
        return True

    def _export_zip(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "保存 ZIP", "export.zip", "ZIP (*.zip)")
        if not path:
            return False
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in self._items:
                if item.file_path and os.path.exists(item.file_path):
                    zf.write(item.file_path, os.path.basename(item.file_path))
        self._show_export_done("ZIP 已打包完成", os.path.dirname(path))
        return True

    def _show_export_done(self, message: str, folder: str):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.information(
            self, "导出完成", message,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open,
        )
        if reply == QMessageBox.StandardButton.Open:
            os.startfile(folder)
