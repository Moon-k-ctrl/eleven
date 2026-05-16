"""Text/HTML preview widget with word wrap and font size controls."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextOption
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class TextPreview(QWidget):
    """Read-only text/HTML display with word wrap and zoomable font."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = 11

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._editor = QTextEdit()
        self._editor.setReadOnly(True)
        self._editor.setAcceptRichText(True)
        self._editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self._editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_style()
        layout.addWidget(self._editor, stretch=1)

        # Font size controls
        zoom_bar = QWidget()
        zoom_bar.setFixedHeight(32)
        zoom_bar.setStyleSheet("background: #252525;")
        zoom_layout = QHBoxLayout(zoom_bar)
        zoom_layout.setContentsMargins(8, 0, 8, 0)
        zoom_layout.setSpacing(6)

        btn_style = (
            "QPushButton { color: #ccc; background: none; border: none;"
            " font-size: 12px; padding: 4px 8px; cursor: pointer; }"
            "QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }"
        )

        zoom_out = QPushButton("A-")
        zoom_out.setStyleSheet(btn_style)
        zoom_out.clicked.connect(lambda: self._change_font_size(-1))
        zoom_layout.addWidget(zoom_out)

        zoom_in = QPushButton("A+")
        zoom_in.setStyleSheet(btn_style)
        zoom_in.clicked.connect(lambda: self._change_font_size(1))
        zoom_layout.addWidget(zoom_in)

        zoom_layout.addStretch()
        layout.addWidget(zoom_bar)

    def _apply_style(self) -> None:
        self._editor.setStyleSheet(f"""
            QTextEdit {{
                background: #1e1e1e;
                color: #e0e0e0;
                border: none;
                padding: 12px;
                font-size: {self._font_size}px;
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                selection-background-color: rgba(100, 149, 237, 0.3);
            }}
        """)

    def _change_font_size(self, delta: int) -> None:
        self._font_size = max(8, min(72, self._font_size + delta))
        font = QFont("Microsoft YaHei", self._font_size)
        self._editor.setFont(font)
        self._apply_style()

    def set_text(self, text: str) -> None:
        self._editor.setPlainText(text)
        self._update_text_width()

    def set_html(self, html: str) -> None:
        self._editor.setHtml(html)
        self._update_text_width()

    def _update_text_width(self) -> None:
        """Set document text width to viewport width for proper word wrap."""
        viewport_width = self._editor.viewport().width()
        if viewport_width > 0:
            self._editor.document().setTextWidth(viewport_width - 24)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_text_width()
