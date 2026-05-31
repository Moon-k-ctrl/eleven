"""Toast notification widget — ink-wash theme (水墨风)."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QLabel, QWidget


class ToastLevel(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


_LEVEL_COLORS = {
    ToastLevel.SUCCESS: "#54D49E",
    ToastLevel.WARNING: "#F2B84B",
    ToastLevel.ERROR: "#F06464",
    ToastLevel.INFO: "#7CE0C3",
}

_LEVEL_ICONS = {
    ToastLevel.SUCCESS: "✓",
    ToastLevel.WARNING: "⚠",
    ToastLevel.ERROR: "✕",
    ToastLevel.INFO: "ℹ",
}


class NotificationToast(QWidget):
    """Auto-dismissing toast notification with ink-wash styling."""

    def __init__(self, message: str, level: ToastLevel = ToastLevel.SUCCESS,
                 duration_ms: int = 2500, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._level = level
        self._message = message
        self._opacity = 0.0
        self._progress = 1.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 44)

        # Icon + message label
        color = _LEVEL_COLORS[level]
        icon = _LEVEL_ICONS[level]
        self._label = QLabel(f"  {icon}  {message}", self)
        self._label.setGeometry(0, 0, 320, 44)
        self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._label.setStyleSheet(
            f"color: #F0F5F2; font-size: 13px; font-family: 'Microsoft YaHei';"
            f"background: transparent;"
        )

        # Fade-in animation
        self._fade_anim = QPropertyAnimation(self, b"opacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Progress animation (shrinks over duration)
        self._progress_anim = QPropertyAnimation(self, b"progress")
        self._progress_anim.setDuration(duration_ms)
        self._progress_anim.setStartValue(1.0)
        self._progress_anim.setEndValue(0.0)
        self._progress_anim.setEasingCurve(QEasingCurve.Type.Linear)

        # Fade-out timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.setInterval(duration_ms)
        self._dismiss_timer.timeout.connect(self._fade_out)

    @pyqtProperty(float)
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, val: float):
        self._opacity = val
        self.update()

    @pyqtProperty(float)
    def progress(self) -> float:
        return self._progress

    @progress.setter
    def progress(self, val: float):
        self._progress = val
        self.update()

    def show_toast(self, x: int, y: int) -> None:
        """Show the toast at (x, y) with fade-in + auto-dismiss."""
        self.move(x, y)
        self.show()
        self._fade_anim.start()
        self._progress_anim.start()
        self._dismiss_timer.start()

    def _fade_out(self) -> None:
        anim = QPropertyAnimation(self, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self.close)
        anim.start()
        self._fade_anim = anim  # prevent GC

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)

        color = QColor(_LEVEL_COLORS[self._level])
        w, h = self.width(), self.height()

        # Background
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 10, 10)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#10161C"))
        p.drawPath(path)

        # Left accent border
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(0, 0, 4, h, 2, 2)

        # Progress bar at bottom
        bar_w = int((w - 8) * self._progress)
        if bar_w > 0:
            bar_color = QColor(color)
            bar_color.setAlpha(80)
            p.setBrush(bar_color)
            p.drawRoundedRect(4, h - 3, bar_w, 2, 1, 1)

        # Border
        p.setPen(QPen(QColor("#29E1EEE7"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(0, 0, w, h, 10, 10)

        p.end()


def show_toast(message: str, level: ToastLevel = ToastLevel.SUCCESS,
               parent: Optional[QWidget] = None, duration_ms: int = 2500) -> NotificationToast:
    """Convenience function: create and show a toast at bottom-center of screen."""
    from PyQt6.QtGui import QGuiApplication
    toast = NotificationToast(message, level, duration_ms, parent)
    screen = QGuiApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - toast.width()) // 2
        y = geo.bottom() - 80
        toast.show_toast(x, y)
    return toast
