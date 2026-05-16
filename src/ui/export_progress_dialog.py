"""Export progress dialog."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout


class ExportProgressDialog(QDialog):
    """Shows export progress with a progress bar."""

    def __init__(self, total: int, parent=None):
        super().__init__(parent)
        self._total = total
        self._cancelled = False
        self.setWindowTitle("导出中...")
        self.setFixedSize(320, 120)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)

        layout = QVBoxLayout(self)

        self._status_label = QLabel(f"正在导出 0 / {total}")
        layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, total)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self._cancel_btn)

    def update_progress(self, current: int) -> None:
        self._progress_bar.setValue(current)
        self._status_label.setText(f"正在导出 {current} / {self._total}")

    def set_done(self, count: int) -> None:
        self._progress_bar.setValue(self._total)
        self._status_label.setText(f"导出完成：{count} 项")
        self._cancel_btn.setText("关闭")

    def _on_cancel(self) -> None:
        self._cancelled = True
        self.close()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
