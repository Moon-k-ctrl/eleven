"""PDF preview widget using PyMuPDF."""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

logger = logging.getLogger("eleven.preview.pdf")


class PdfPreview(QWidget):
    """PDF page renderer using PyMuPDF (fitz)."""

    page_changed = pyqtSignal(int, int)  # current, total
    zoom_changed = pyqtSignal(int)       # zoom percent

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = None
        self._current_page = 0
        self._total_pages = 0
        self._zoom = 1.5

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { background: #1a1a1a; border: none; }")
        self._page_label = QLabel()
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setWidget(self._page_label)
        layout.addWidget(self._scroll)

    def load_pdf(self, path: str) -> None:
        try:
            import fitz
            self._doc = fitz.open(path)
            self._total_pages = len(self._doc)
            self._current_page = 0
            self._render_page()
            self.page_changed.emit(self._current_page + 1, self._total_pages)
            self.zoom_changed.emit(int(self._zoom * 100))
        except ImportError:
            self._page_label.setText("需要安装 PyMuPDF: pip install pymupdf")
            self._page_label.setStyleSheet("color: #ff6b6b; font-size: 14px;")
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            self._page_label.setText(f"加载失败: {e}")
            self._page_label.setStyleSheet("color: #ff6b6b; font-size: 14px;")

    def _render_page(self) -> None:
        if not self._doc or self._current_page < 0 or self._current_page >= self._total_pages:
            return
        try:
            import fitz
            page = self._doc[self._current_page]
            mat = fitz.Matrix(self._zoom, self._zoom)
            pix = page.get_pixmap(matrix=mat)
            img = QImage(pix.samples, pix.width, pix.height,
                         pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            self._page_label.setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Failed to render page: {e}")
            self._page_label.setText(f"渲染失败: {e}")

    def next_page(self) -> None:
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._render_page()
            self.page_changed.emit(self._current_page + 1, self._total_pages)

    def prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._render_page()
            self.page_changed.emit(self._current_page + 1, self._total_pages)

    def goto_page(self, index: int) -> None:
        if 0 <= index < self._total_pages:
            self._current_page = index
            self._render_page()
            self.page_changed.emit(self._current_page + 1, self._total_pages)

    def total_pages(self) -> int:
        return self._total_pages

    def zoom_in(self) -> None:
        self._zoom = min(self._zoom + 0.25, 5.0)
        self._render_page()
        self.zoom_changed.emit(int(self._zoom * 100))

    def zoom_out(self) -> None:
        self._zoom = max(self._zoom - 0.25, 0.5)
        self._render_page()
        self.zoom_changed.emit(int(self._zoom * 100))

    def fit_window(self) -> None:
        self._zoom = 1.5
        self._render_page()
        self.zoom_changed.emit(int(self._zoom * 100))

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def cleanup(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None
