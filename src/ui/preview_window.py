"""Standalone preview window for clipboard item content."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.clipboard_item import ClipboardItem, ContentType

logger = logging.getLogger("eleven.preview")


PREVIEW_STYLE = """
QWidget {
    background: #121212;
    color: #e0e0e0;
}
QPushButton {
    background: #2a2a2a;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ccc;
    font-size: 12px;
}
QPushButton:hover {
    background: #3a3a3a;
    color: white;
}
QLabel {
    color: #aaa;
    font-size: 12px;
}
"""


class PreviewWindow(QWidget):
    """Standalone preview window for a clipboard item."""

    def __init__(self, item: ClipboardItem, parent=None):
        super().__init__(parent)
        self._item = item
        self._is_fullscreen = False
        self._content_widget: Optional[QWidget] = None
        self._setup_window()
        self._setup_ui()
        self._load_content()

    def _setup_window(self) -> None:
        title = self._item.short_preview(40) or f"预览 #{self._item.id}"
        self.setWindowTitle(f"预览 - {title}")
        self.setStyleSheet(PREVIEW_STYLE)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            w = int(geo.width() * 0.7)
            h = int(geo.height() * 0.8)
            self.resize(w, h)
            self.move(
                geo.x() + (geo.width() - w) // 2,
                geo.y() + (geo.height() - h) // 2,
            )
        else:
            self.resize(900, 700)

        self.setMinimumSize(640, 420)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 内容区域（由具体渲染器填充）
        self._content_area = QWidget()
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._content_area, 1)

        # 底部工具栏
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet("background: #252525;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 0, 8, 0)
        tb_layout.setSpacing(6)

        # 关闭按钮（最左侧）
        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(28, 24)
        self._close_btn.clicked.connect(self.close)
        tb_layout.addWidget(self._close_btn)

        # 标题标签
        title = Path(self._item.file_path).name if self._item.file_path else "预览"
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self._title_label.setFixedWidth(120)
        tb_layout.addWidget(self._title_label)

        # 缩放按钮（图片/PDF）
        self._zoom_out_btn = QPushButton("-")
        self._zoom_out_btn.setFixedSize(28, 24)
        self._zoom_out_btn.clicked.connect(self._on_zoom_out)
        tb_layout.addWidget(self._zoom_out_btn)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(48)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_layout.addWidget(self._zoom_label)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedSize(28, 24)
        self._zoom_in_btn.clicked.connect(self._on_zoom_in)
        tb_layout.addWidget(self._zoom_in_btn)

        self._fit_btn = QPushButton("适应")
        self._fit_btn.setFixedSize(40, 24)
        self._fit_btn.clicked.connect(self._on_fit)
        tb_layout.addWidget(self._fit_btn)

        # 翻页按钮（PDF/PPT）
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedSize(28, 24)
        self._prev_btn.clicked.connect(self._on_prev)
        tb_layout.addWidget(self._prev_btn)

        self._page_label = QLabel("1 / 1")
        self._page_label.setFixedWidth(60)
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_layout.addWidget(self._page_label)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedSize(28, 24)
        self._next_btn.clicked.connect(self._on_next)
        tb_layout.addWidget(self._next_btn)

        tb_layout.addStretch()

        # 复制按钮（仅 TEXT/HTML 可见）
        self._copy_btn = QPushButton("复制")
        self._copy_btn.clicked.connect(self._on_copy)
        tb_layout.addWidget(self._copy_btn)

        # 打开按钮（有文件路径时可见）
        self._open_btn = QPushButton("打开")
        self._open_btn.clicked.connect(self._on_open)
        tb_layout.addWidget(self._open_btn)

        # 全屏按钮
        self._fullscreen_btn = QPushButton("全屏")
        self._fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        tb_layout.addWidget(self._fullscreen_btn)

        layout.addWidget(toolbar)

        # 根据类型隐藏不需要的按钮
        self._update_toolbar_visibility()

    def _get_file_path(self) -> Optional[str]:
        """Get the actual file path from item, checking file_path first then content_text."""
        if self._item.file_path:
            return self._item.file_path
        if self._item.content_type == ContentType.FILES and self._item.content_text:
            first = self._item.content_text.split("\n")[0].strip()
            if first and Path(first).exists():
                return first
        return None

    def _get_display_type(self) -> str:
        """Get effective display type, with fallback for FILES type."""
        dt = self._item.display_type
        if dt != "files":
            return dt
        # Fallback: inspect file extension from content_text
        fpath = self._get_file_path()
        if fpath:
            ext = Path(fpath).suffix.lower()
            ext_map = {
                ".pdf": "pdf", ".doc": "word", ".docx": "word",
                ".xls": "excel", ".xlsx": "excel",
                ".ppt": "ppt", ".pptx": "ppt",
                ".md": "markdown", ".markdown": "markdown",
                ".png": "image", ".jpg": "image", ".jpeg": "image",
                ".gif": "image", ".webp": "image", ".bmp": "image",
                ".svg": "image", ".ico": "image",
                ".txt": "text_file", ".log": "text_file", ".py": "text_file",
                ".js": "text_file", ".json": "text_file", ".xml": "text_file",
                ".csv": "text_file", ".yaml": "text_file", ".yml": "text_file",
                ".html": "html", ".htm": "html",
            }
            return ext_map.get(ext, "files")
        return dt

    def _update_toolbar_visibility(self) -> None:
        dt = self._get_display_type()
        has_zoom = dt in ("image", "pdf")
        has_pages = dt in ("pdf", "ppt")
        has_copy = dt in ("text", "html")
        has_open = self._get_file_path() is not None

        self._zoom_out_btn.setVisible(has_zoom)
        self._zoom_label.setVisible(has_zoom)
        self._zoom_in_btn.setVisible(has_zoom)
        self._fit_btn.setVisible(has_zoom)
        self._prev_btn.setVisible(has_pages)
        self._page_label.setVisible(has_pages)
        self._next_btn.setVisible(has_pages)
        self._copy_btn.setVisible(has_copy)
        self._open_btn.setVisible(has_open)

    def _load_content(self) -> None:
        dt = self._get_display_type()
        fpath = self._get_file_path()
        logger.info(f"Preview: display_type={dt}, file_path={fpath}, "
                     f"content_type={self._item.content_type}")

        try:
            if dt == "text" or dt == "html":
                from src.ui.previews.text_preview import TextPreview
                widget = TextPreview()
                if dt == "html" and self._item.content_html:
                    widget.set_html(self._item.content_html)
                else:
                    widget.set_text(self._item.content_text or "")
                self._set_content(widget)

            elif dt == "image":
                if fpath:
                    from src.ui.previews.image_preview import ImagePreview
                    widget = ImagePreview()
                    widget.load_image(fpath)
                    self._set_content(widget)
                else:
                    self._show_error("图片文件路径无效")

            elif dt == "pdf":
                if fpath:
                    from src.ui.previews.pdf_preview import PdfPreview
                    widget = PdfPreview()
                    widget.page_changed.connect(self._on_page_changed)
                    widget.zoom_changed.connect(self._on_zoom_changed)
                    widget.load_pdf(fpath)
                    self._set_content(widget)
                else:
                    self._show_error("PDF 文件路径无效")

            elif dt == "word":
                if fpath:
                    from src.ui.previews.word_preview import WordPreview
                    widget = WordPreview()
                    widget.load_docx(fpath)
                    self._set_content(widget)
                else:
                    self._show_error("Word 文件路径无效")

            elif dt == "excel":
                if fpath:
                    from src.ui.previews.excel_preview import ExcelPreview
                    widget = ExcelPreview()
                    widget.load_xlsx(fpath)
                    self._set_content(widget)
                else:
                    self._show_error("Excel 文件路径无效")

            elif dt == "ppt":
                if fpath:
                    from src.ui.previews.ppt_preview import PptPreview
                    widget = PptPreview()
                    widget.slide_changed.connect(self._on_page_changed)
                    widget.load_pptx(fpath)
                    self._set_content(widget)
                else:
                    self._show_error("PPT 文件路径无效")

            elif dt == "markdown":
                from src.ui.previews.markdown_preview import MarkdownPreview
                widget = MarkdownPreview()
                text = self._item.content_text or ""
                if fpath:
                    try:
                        text = Path(fpath).read_text(encoding="utf-8")
                    except Exception:
                        pass
                widget.load_markdown(text)
                self._set_content(widget)

            elif dt == "text_file":
                from src.ui.previews.text_preview import TextPreview
                widget = TextPreview()
                if fpath:
                    try:
                        text = Path(fpath).read_text(encoding="utf-8", errors="replace")
                        widget.set_text(text)
                    except Exception as e:
                        widget.set_text(f"无法读取文件: {fpath}\n错误: {e}")
                else:
                    widget.set_text(self._item.content_text or "")
                self._set_content(widget)

            else:
                # 最终兜底：尝试按扩展名打开
                if fpath:
                    self._try_open_by_extension(fpath)
                else:
                    self._show_error(f"不支持预览此类型: {dt}")

        except Exception as e:
            logger.error(f"Failed to load preview: {e}", exc_info=True)
            self._show_error(f"加载失败: {e}")

    def _try_open_by_extension(self, fpath: str) -> None:
        """Last resort: try to open file based on extension."""
        ext = Path(fpath).suffix.lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
            from src.ui.previews.image_preview import ImagePreview
            widget = ImagePreview()
            widget.load_image(fpath)
            self._set_content(widget)
        elif ext == ".pdf":
            from src.ui.previews.pdf_preview import PdfPreview
            widget = PdfPreview()
            widget.page_changed.connect(self._on_page_changed)
            widget.zoom_changed.connect(self._on_zoom_changed)
            widget.load_pdf(fpath)
            self._set_content(widget)
        elif ext in (".doc", ".docx"):
            from src.ui.previews.word_preview import WordPreview
            widget = WordPreview()
            widget.load_docx(fpath)
            self._set_content(widget)
        elif ext in (".xls", ".xlsx"):
            from src.ui.previews.excel_preview import ExcelPreview
            widget = ExcelPreview()
            widget.load_xlsx(fpath)
            self._set_content(widget)
        elif ext in (".ppt", ".pptx"):
            from src.ui.previews.ppt_preview import PptPreview
            widget = PptPreview()
            widget.slide_changed.connect(self._on_page_changed)
            widget.load_pptx(fpath)
            self._set_content(widget)
        elif ext in (".md", ".markdown"):
            from src.ui.previews.markdown_preview import MarkdownPreview
            widget = MarkdownPreview()
            try:
                text = Path(fpath).read_text(encoding="utf-8")
                widget.load_markdown(text)
            except Exception:
                widget.load_markdown(f"无法读取: {fpath}")
            self._set_content(widget)
        else:
            from src.ui.previews.text_preview import TextPreview
            widget = TextPreview()
            try:
                text = Path(fpath).read_text(encoding="utf-8", errors="replace")
                widget.set_text(text)
            except Exception:
                self._show_error(f"无法预览此文件: {Path(fpath).name}")
                return
            self._set_content(widget)

    def _show_error(self, msg: str) -> None:
        label = QLabel(msg)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #ff6b6b; font-size: 14px;")
        self._set_content(label)

    def _set_content(self, widget: QWidget) -> None:
        if self._content_widget:
            self._content_widget.deleteLater()
        self._content_widget = widget
        self._content_layout.addWidget(widget)

    def _on_page_changed(self, current: int, total: int) -> None:
        self._page_label.setText(f"{current} / {total}")

    def _on_zoom_changed(self, zoom: int) -> None:
        self._zoom_label.setText(f"{zoom}%")

    def _on_zoom_in(self) -> None:
        if self._content_widget and hasattr(self._content_widget, 'zoom_in'):
            self._content_widget.zoom_in()

    def _on_zoom_out(self) -> None:
        if self._content_widget and hasattr(self._content_widget, 'zoom_out'):
            self._content_widget.zoom_out()

    def _on_fit(self) -> None:
        if self._content_widget and hasattr(self._content_widget, 'fit_window'):
            self._content_widget.fit_window()

    def _on_copy(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard and self._item.content_text:
            clipboard.setText(self._item.content_text)

    def _on_open(self) -> None:
        fpath = self._get_file_path()
        if fpath:
            os.startfile(fpath)

    def _on_prev(self) -> None:
        if self._content_widget and hasattr(self._content_widget, 'prev_page'):
            self._content_widget.prev_page()
        elif self._content_widget and hasattr(self._content_widget, 'prev_slide'):
            self._content_widget.prev_slide()

    def _on_next(self) -> None:
        if self._content_widget and hasattr(self._content_widget, 'next_page'):
            self._content_widget.next_page()
        elif self._content_widget and hasattr(self._content_widget, 'next_slide'):
            self._content_widget.next_slide()

    def _on_first_page(self) -> None:
        if self._content_widget and hasattr(self._content_widget, 'goto_page'):
            self._content_widget.goto_page(0)
        elif self._content_widget and hasattr(self._content_widget, 'goto_slide'):
            self._content_widget.goto_slide(0)

    def _on_last_page(self) -> None:
        if self._content_widget and hasattr(self._content_widget, 'total_pages'):
            total = self._content_widget.total_pages()
            if total > 0:
                self._on_page_changed(total, total)
                if hasattr(self._content_widget, 'goto_page'):
                    self._content_widget.goto_page(total - 1)
        elif self._content_widget and hasattr(self._content_widget, 'total_slides'):
            total = self._content_widget.total_slides
            if total > 0:
                self._on_page_changed(total, total)
                if hasattr(self._content_widget, 'goto_slide'):
                    self._content_widget.goto_slide(total - 1)

    def toggle_fullscreen(self) -> None:
        if self._is_fullscreen:
            self.showNormal()
            self._fullscreen_btn.setText("全屏")
        else:
            self.showFullScreen()
            self._fullscreen_btn.setText("退出全屏")
        self._is_fullscreen = not self._is_fullscreen

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if not event:
            return super().keyPressEvent(event)
        key = event.key()
        if key == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self.toggle_fullscreen()
            else:
                self.close()
        elif key == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_PageUp):
            self._on_prev()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_PageDown):
            self._on_next()
        elif key == Qt.Key.Key_Home:
            self._on_first_page()
        elif key == Qt.Key.Key_End:
            self._on_last_page()
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._on_zoom_in()
        elif key == Qt.Key.Key_Minus:
            self._on_zoom_out()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event) -> None:
        """Ctrl+scroll zoom for image previews."""
        if (event is not None
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
                and self._content_widget
                and hasattr(self._content_widget, '_view')):
            delta = event.angleDelta().y()
            if delta > 0:
                self._on_zoom_in()
            else:
                self._on_zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Double-click toggles between fit-in-view and 100% for image previews."""
        if (self._content_widget
                and hasattr(self._content_widget, '_view')
                and hasattr(self._content_widget, 'fit_window')
                and hasattr(self._content_widget, 'reset_zoom')):
            if self._content_widget._zoom != 1.0:
                self._content_widget.reset_zoom()
            else:
                self._content_widget.fit_window()
            self._zoom_label.setText(f"{int(self._content_widget._zoom * 100)}%")
        super().mouseDoubleClickEvent(event)

    def closeEvent(self, event) -> None:
        if self._content_widget:
            # 清理资源（如 PyMuPDF document handle）
            if hasattr(self._content_widget, 'cleanup'):
                self._content_widget.cleanup()
        super().closeEvent(event)
