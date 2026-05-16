"""Floating ball widget — draggable circle that accepts file drops, with badge."""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QApplication, QWidget

logger = logging.getLogger("eleven.ball")

BALL_SIZE = 96
BALL_INNER = 88
BALL_RADIUS = BALL_INNER / 2
BALL_OFFSET = (BALL_SIZE - BALL_INNER) / 2
BADGE_H = 22
BADGE_MIN_W = 22


class FloatingBall(QWidget):
    """A small always-on-top floating ball that accepts file drops."""

    files_dropped = pyqtSignal(list)
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos: Optional[QPoint] = None
        self._count = 0
        self._hovered = False
        self._drag_over = False
        self._setup_window()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFixedSize(BALL_SIZE + BADGE_MIN_W, BALL_SIZE + BADGE_H)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 12, geo.bottom() - self.height() - 12)

    def update_badge(self, count: int) -> None:
        self._count = count
        self.update()

    # ── Painting ──

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = BALL_SIZE / 2, BALL_SIZE / 2
        r = BALL_RADIUS

        # --- Ball body ---
        grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        if self._drag_over:
            grad.setColorAt(0, QColor(67, 233, 123, 220))
            grad.setColorAt(1, QColor(56, 249, 215, 220))
        elif self._hovered:
            grad.setColorAt(0, QColor(90, 160, 230, 240))
            grad.setColorAt(1, QColor(74, 144, 217, 240))
        else:
            grad.setColorAt(0, QColor(74, 144, 217, 220))
            grad.setColorAt(1, QColor(58, 110, 180, 220))

        border_alpha = 100 if (self._hovered or self._drag_over) else 50
        p.setPen(QPen(QColor(255, 255, 255, border_alpha), 2))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # --- Icon ---
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI Emoji", 28))
        p.drawText(QRectF(0, 0, BALL_SIZE, BALL_SIZE), Qt.AlignmentFlag.AlignCenter, "📋")

        # --- Badge (drawn last, on top, NO clipping) ---
        if self._count > 0:
            badge_text = str(min(self._count, 99)) + ("+" if self._count > 99 else "")
            fm = p.fontMetrics()
            text_w = fm.horizontalAdvance(badge_text)
            bw = max(BADGE_MIN_W, text_w + 10)
            bh = BADGE_H
            bx = BALL_SIZE - 4
            by = 2

            badge_path = QPainterPath()
            badge_path.addRoundedRect(QRectF(bx, by, bw, bh), bh / 2, bh / 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 68, 68))
            p.drawPath(badge_path)

            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, badge_text)

        p.end()

    # ── Mouse events ──

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_pos:
                moved = (event.globalPosition().toPoint()
                         - self.frameGeometry().topLeft() - self._drag_pos)
                if moved.manhattanLength() < 5:
                    self.clicked.emit()
            self._drag_pos = None
            event.accept()

    # ── Drag-drop ──

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drag_over = True
            self.update()

    def dragLeaveEvent(self, event) -> None:
        self._drag_over = False
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:
        self._drag_over = False
        self.update()
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
            event.acceptProposedAction()

    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
