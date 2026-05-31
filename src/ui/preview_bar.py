"""PreviewBar — floating ball that morphs into a side preview strip.

State machine:
  "ball"    → 96x96 window, gradient circle, badge
  "preview" → dynamic width, thumbnail strip + action area
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QPoint, QPointF, QRectF,
    QPropertyAnimation, Qt, QTimer, QUrl, pyqtSignal,
    pyqtProperty, QParallelAnimationGroup,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDrag, QLinearGradient,
    QPainter, QPainterPath, QPen, QPixmap, QRadialGradient,
)
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from src.models.clipboard_item import ClipboardItem, ContentType
from src.ui.drag_handler import DragHandler
from src.ui.qml.theme_singleton import ThemeSingleton

logger = logging.getLogger("eleven.preview_bar")

# ── 尺寸常量 ──
BALL_VISIBLE = 80          # 可见圆直径
BADGE_W = 22
BADGE_H = 22
BALL_MARGIN_SIDE = 14      # 左右下边距（增大底部空间给阴影）
BALL_MARGIN_TOP = BADGE_H  # 顶部留出角标高度
BALL_WINDOW_W = BALL_VISIBLE + BALL_MARGIN_SIDE * 2   # = 116
BALL_WINDOW_H = BALL_VISIBLE + BALL_MARGIN_TOP + BALL_MARGIN_SIDE  # = 124

# 状态颜色映射
STATUS_COLORS = {
    "online": QColor(76, 175, 80),
    "warning": QColor(255, 152, 0),
    "error": QColor(244, 67, 54),
    "offline": QColor(117, 117, 117),
}
STATUS_LABELS = {"online": "在线", "warning": "警告", "error": "错误", "offline": "离线"}

THUMB_SIZE = 48
THUMB_GAP = 6
THUMB_PADDING = 10
ACTION_AREA_W = 40
MAX_VISIBLE_THUMBS = 8

# Vertical list layout constants
VLIST_ITEM_H = 64       # 每行高度
VLIST_THUMB = 40        # 缩略图尺寸
VLIST_PADDING = 12      # 内边距
VLIST_W = 320           # 预览栏宽度
VLIST_MIN_H = 120       # 最小高度
VLIST_MAX_H = 400       # 最大高度

# Staging shelf layout constants (暂存架)
STAGING_CARD_SIZE = 72   # 卡片尺寸
STAGING_GAP = 6          # 卡片间距
STAGING_PADDING = 10     # 内边距
STAGING_COLS = 3         # 列数
STAGING_W = STAGING_PADDING * 2 + STAGING_COLS * STAGING_CARD_SIZE + (STAGING_COLS - 1) * STAGING_GAP  # = 260
STAGING_HEADER_H = 32    # 标题栏高度
STAGING_FOOTER_H = 24    # 底部高度
STAGING_MAX_CARDS = 9    # 最多显示 3x3


class PreviewBar(QWidget):
    """Floating ball ↔ preview strip morphing widget."""

    item_dragged_out = pyqtSignal(ClipboardItem)
    all_cleared = pyqtSignal()
    expand_requested = pyqtSignal()
    files_dropped = pyqtSignal(list)
    clicked = pyqtSignal()
    quit_requested = pyqtSignal()
    toggle_monitoring_requested = pyqtSignal()
    panel_show_requested = pyqtSignal()
    hide_ball_requested = pyqtSignal()
    copy_item_requested = pyqtSignal(int)
    preview_item_requested = pyqtSignal(object)
    remove_item_requested = pyqtSignal(int)
    staging_file_dropped = pyqtSignal(list)  # files dropped onto staging shelf

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[ClipboardItem] = []
        self._staging_items: list[dict] = []  # staging shelf items (dicts from DB)
        self._mode = "ball"  # "ball" | "preview" | "staging"
        self._count = 0  # badge count (total items in DB)
        self._status = "offline"  # "online" | "warning" | "error" | "offline"
        self._theme = ThemeSingleton()
        self._morph_progress = 0.0

        # Interaction state
        self._hovered = False
        self._drag_over = False
        self._hovered_index = -1
        self._hovered_btn = ""  # "expand" | "close" | ""
        self._dragging_index = -1
        self._drag_start_pos: Optional[QPoint] = None
        self._drag_start_index = -1
        self._scroll_offset = 0

        # Ball drag (reposition)
        self._ball_drag_pos: Optional[QPoint] = None
        self._saved_ball_pos: Optional[tuple[int, int]] = None  # for position restore after morph

        # Drag-over ring animation
        self._ring_phase = 0.0
        self._ring_timer = QTimer(self)
        self._ring_timer.timeout.connect(self._animate_ring)
        # Success flash
        self._flash_active = False
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._end_flash)

        # Hover transition (120ms)
        self._hover_progress = 0.0  # 0.0 = default, 1.0 = hovered
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(16)  # ~60fps
        self._hover_timer.timeout.connect(self._animate_hover)
        # Press scale
        self._press_scale = 1.0
        self._pressed = False
        # Breathing animation for status dot
        self._breath_phase = 0.0
        self._breath_timer = QTimer(self)
        self._breath_timer.setInterval(33)
        self._breath_timer.timeout.connect(self._animate_breath)

        # Long hover timer (ball → preview expansion)
        self._long_hover_timer = QTimer(self)
        self._long_hover_timer.setSingleShot(True)
        self._long_hover_timer.setInterval(600)
        self._long_hover_timer.timeout.connect(self._on_long_hover)

        # Ball dragging state to prevent hover trigger
        self._is_dragging_ball = False

        # Animation lock to prevent interactions during morph
        self._is_animating = False

        self._setup_window()

    # ── Window setup ──

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self._update_geometry_for_ball()

    def _update_geometry_for_ball(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        # 尝试加载保存的位置
        saved = self._load_position()
        if saved:
            x, y = saved
            # 确保在屏幕范围内
            if x < geo.left() or x > geo.right() - BALL_WINDOW_W:
                x = geo.right() - BALL_WINDOW_W - 20
            if y < geo.top() or y > geo.bottom() - BALL_WINDOW_H:
                y = geo.bottom() - BALL_WINDOW_H - 20
        else:
            x = geo.right() - BALL_WINDOW_W - 20
            y = geo.bottom() - BALL_WINDOW_H - 20
        self.setGeometry(x, y, BALL_WINDOW_W, BALL_WINDOW_H)

    @pyqtProperty(float)
    def morph_progress(self) -> float:
        return self._morph_progress

    @morph_progress.setter
    def morph_progress(self, val: float):
        self._morph_progress = val
        self.update()

    @staticmethod
    def _load_position() -> tuple[int, int] | None:
        try:
            from src.core.config import Config
            return Config().get_ball_position()
        except Exception:
            return None

    # ── Public API ──

    def update_badge(self, count: int):
        self._count = count
        self.update()

    def update_status(self, status: str):
        self._status = status
        if status == "warning":
            self._breath_timer.start()
        else:
            self._breath_timer.stop()
        if self._mode == "ball":
            self.update()

    def _animate_ring(self):
        self._ring_phase = (self._ring_phase + 0.08) % 1.0
        self.update()

    def _end_flash(self):
        self._flash_active = False
        self._flash_timer.stop()
        self.update()

    def _animate_hover(self):
        target = 1.0 if self._hovered else 0.0
        step = 0.12  # ~120ms at 60fps (16ms interval)
        if abs(self._hover_progress - target) < step:
            self._hover_progress = target
            self._hover_timer.stop()
        elif self._hover_progress < target:
            self._hover_progress = min(target, self._hover_progress + step)
        else:
            self._hover_progress = max(target, self._hover_progress - step)
        self.update()

    def _animate_breath(self):
        self._breath_phase = (self._breath_phase + 0.02) % 1.0
        self.update()

    def add_items(self, items: list[ClipboardItem]):
        self._items.extend(items)
        if self._mode == "ball" and self._items:
            self._morph_to_preview()
        else:
            self.update()

    def remove_item(self, item: ClipboardItem):
        self._items = [i for i in self._items if i.id != item.id]
        self.item_dragged_out.emit(item)
        if not self._items:
            self._morph_to_ball()
        else:
            self.update()

    def clear(self):
        self._items.clear()
        self._morph_to_ball()

    def set_items(self, items: list):
        """Replace items without triggering morph animation."""
        self._items = list(items)
        self.update()

    def set_staging_items(self, items: list[dict]):
        """Update staging shelf items from DB."""
        self._staging_items = list(items)[:STAGING_MAX_CARDS]
        if self._mode == "staging":
            self._recalc_staging_geometry()
            self.update()

    def _recalc_staging_geometry(self):
        """Recalculate window size for current staging items count."""
        visible = max(1, len(self._staging_items))
        rows = (visible + STAGING_COLS - 1) // STAGING_COLS
        target_h = STAGING_HEADER_H + rows * (STAGING_CARD_SIZE + STAGING_GAP) + STAGING_FOOTER_H + STAGING_PADDING
        target_h = max(STAGING_HEADER_H + STAGING_CARD_SIZE + STAGING_FOOTER_H + STAGING_PADDING * 2, target_h)
        geo = self.geometry()
        self.setGeometry(geo.x(), geo.y(), STAGING_W, target_h)

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    # ── Morphing animation ──

    def _morph_to_preview(self):
        if self._is_animating:
            return
        self._is_animating = True
        self._long_hover_timer.stop()
        # Save ball position before morphing (for #6 position restore)
        self._saved_ball_pos = (self.x(), self.y())

        visible = min(len(self._items), MAX_VISIBLE_THUMBS)
        target_w = VLIST_W
        target_h = VLIST_PADDING + visible * VLIST_ITEM_H + VLIST_PADDING + ACTION_AREA_W
        target_h = max(VLIST_MIN_H, min(VLIST_MAX_H, target_h))

        screen = QApplication.primaryScreen()
        if not screen:
            self._is_animating = False
            return
        geo = screen.availableGeometry()
        target_x = geo.right() - target_w - 8
        target_y = self.y()

        self._morph_progress = 0.0

        geom_anim = QPropertyAnimation(self, b"geometry")
        geom_anim.setDuration(350)
        geom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        geom_anim.setStartValue(self.geometry())
        geom_anim.setEndValue(self._make_rect(target_x, target_y, target_w, target_h))

        progress_anim = QPropertyAnimation(self, b"morph_progress")
        progress_anim.setDuration(350)
        progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        progress_anim.setStartValue(0.0)
        progress_anim.setEndValue(1.0)

        group = QParallelAnimationGroup(self)
        group.addAnimation(geom_anim)
        group.addAnimation(progress_anim)
        group.finished.connect(self._on_preview_morph_finished)
        group.start()
        self._morph_anim = group  # prevent GC

    def _on_preview_morph_finished(self):
        self._mode = "preview"
        self._morph_progress = 1.0
        self._is_animating = False
        self._long_hover_timer.stop()
        self.update()

    def _morph_to_ball(self):
        if self._is_animating:
            return
        self._is_animating = True
        self._scroll_offset = 0
        # Restore saved ball position if available, otherwise use default
        if self._saved_ball_pos:
            target_x, target_y = self._saved_ball_pos
        else:
            screen = QApplication.primaryScreen()
            if not screen:
                self._is_animating = False
                return
            geo = screen.availableGeometry()
            target_x = geo.right() - BALL_WINDOW_W - 20
            target_y = geo.bottom() - BALL_WINDOW_H - 20

        self._morph_progress = 1.0

        geom_anim = QPropertyAnimation(self, b"geometry")
        geom_anim.setDuration(300)
        geom_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        geom_anim.setStartValue(self.geometry())
        geom_anim.setEndValue(self._make_rect(target_x, target_y, BALL_WINDOW_W, BALL_WINDOW_H))

        progress_anim = QPropertyAnimation(self, b"morph_progress")
        progress_anim.setDuration(300)
        progress_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        progress_anim.setStartValue(1.0)
        progress_anim.setEndValue(0.0)

        group = QParallelAnimationGroup(self)
        group.addAnimation(geom_anim)
        group.addAnimation(progress_anim)
        group.finished.connect(self._on_ball_morph_finished)
        group.start()
        self._morph_anim = group

    def _on_ball_morph_finished(self):
        self._mode = "ball"
        self._morph_progress = 0.0
        self._is_animating = False
        self.all_cleared.emit()
        self.update()

    def _morph_to_staging(self):
        """Morph from ball to staging shelf grid."""
        if self._is_animating:
            return
        self._is_animating = True
        self._long_hover_timer.stop()
        self._saved_ball_pos = (self.x(), self.y())

        visible = max(1, len(self._staging_items))
        rows = (visible + STAGING_COLS - 1) // STAGING_COLS
        target_w = STAGING_W
        target_h = STAGING_HEADER_H + rows * (STAGING_CARD_SIZE + STAGING_GAP) + STAGING_FOOTER_H + STAGING_PADDING
        target_h = max(STAGING_HEADER_H + STAGING_CARD_SIZE + STAGING_FOOTER_H + STAGING_PADDING * 2, target_h)

        screen = QApplication.primaryScreen()
        if not screen:
            self._is_animating = False
            return
        geo = screen.availableGeometry()
        # Position: to the left of the ball's current position
        ball_x = self.x()
        target_x = ball_x - target_w + BALL_WINDOW_W
        target_x = max(geo.left() + 4, min(target_x, geo.right() - target_w - 4))
        target_y = self.y()

        self._morph_progress = 0.0

        geom_anim = QPropertyAnimation(self, b"geometry")
        geom_anim.setDuration(300)
        geom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        geom_anim.setStartValue(self.geometry())
        geom_anim.setEndValue(self._make_rect(target_x, target_y, target_w, target_h))

        progress_anim = QPropertyAnimation(self, b"morph_progress")
        progress_anim.setDuration(300)
        progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        progress_anim.setStartValue(0.0)
        progress_anim.setEndValue(1.0)

        group = QParallelAnimationGroup(self)
        group.addAnimation(geom_anim)
        group.addAnimation(progress_anim)
        group.finished.connect(self._on_staging_morph_finished)
        group.start()
        self._morph_anim = group

    def _on_staging_morph_finished(self):
        self._mode = "staging"
        self._morph_progress = 1.0
        self._is_animating = False
        self.update()

    @staticmethod
    def _make_rect(x, y, w, h):
        from PyQt6.QtCore import QRect
        return QRect(int(x), int(y), int(w), int(h))

    # ── Painting ──

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._is_animating:
            t = self._morph_progress
            if t < 0.5:
                p.save()
                p.setOpacity(1.0 - t)
                self._paint_ball(p)
                p.restore()

                p.save()
                p.setOpacity(t)
                if self._mode == "staging" or (self._mode == "ball" and self._drag_over):
                    self._paint_staging_grid(p)
                else:
                    self._paint_preview_bar(p)
                p.restore()
            else:
                p.save()
                p.setOpacity(t)
                if self._mode == "staging" or (self._mode == "ball" and self._drag_over):
                    self._paint_staging_grid(p)
                else:
                    self._paint_preview_bar(p)
                p.restore()

                p.save()
                p.setOpacity(1.0 - t)
                self._paint_ball(p)
                p.restore()
        elif self._mode == "ball":
            self._paint_ball(p)
        elif self._mode == "staging":
            self._paint_staging_grid(p)
        else:
            self._paint_preview_bar(p)
        p.end()

    def _paint_ball(self, p: QPainter):
        from PyQt6.QtGui import QFont
        import math
        
        # Calculate dynamic bx
        w = self.width()
        if self._is_animating:
            bx = w - BALL_VISIBLE - BALL_MARGIN_SIDE
        else:
            bx = BALL_MARGIN_SIDE
            
        by = BALL_MARGIN_TOP - 4
        cx = bx + BALL_VISIBLE / 2
        cy = by + BALL_VISIBLE / 2
        r = BALL_VISIBLE / 2

        # Draw scaled-down and shadowed under pressed state
        p.save()
        if self._pressed:
            p.translate(cx, cy)
            p.scale(0.96, 0.96)
            p.translate(-cx, -cy)

        # Shadow — mint-green tinted, matching design spec rgba(84,212,158,0.28)
        for i in range(5, 0, -1):
            alpha = int(18 * (6 - i))       # 90, 72, 54, 36, 18
            offset = 3 + i                   # 8, 7, 6, 5, 4
            spread = i * 2 + 2              # 12, 10, 8, 6, 4
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(84, 212, 158, alpha))
            p.drawEllipse(
                int(bx - spread // 2), int(by + offset - spread // 2),
                BALL_VISIBLE + spread, BALL_VISIBLE + spread
            )

        # Drag-over: pulsing dashed ring
        if self._drag_over:
            ring_r = r + 6 + math.sin(self._ring_phase * math.pi * 2) * 3
            p.setPen(QPen(QColor(0x7C, 0xE0, 0xC3, 180), 2, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        # Success flash overlay
        if self._flash_active:
            grad = QLinearGradient(bx, by, bx + BALL_VISIBLE, by + BALL_VISIBLE)
            grad.setColorAt(0, QColor(0x7C, 0xE0, 0xC3, 200))
            grad.setColorAt(1, QColor(0x54, 0xD4, 0x9E, 200))
        elif self._drag_over:
            grad = QLinearGradient(bx, by, bx + BALL_VISIBLE, by + BALL_VISIBLE)
            grad.setColorAt(0, QColor(0x7C, 0xE0, 0xC3))
            grad.setColorAt(1, QColor(0x54, 0xD4, 0x9E))
        else:
            # Smooth hover transition using _hover_progress — 曜石青渐变
            t = self._hover_progress
            # accent-mint #7CE0C3 → hover slightly brighter
            r1 = int(0x7C + (0x8C - 0x7C) * t)
            g1 = int(0xE0 + (0xF0 - 0xE0) * t)
            b1 = int(0xC3 + (0xD3 - 0xC3) * t)
            # accent-blue #66B8C7 → hover slightly brighter
            r2 = int(0x66 + (0x76 - 0x66) * t)
            g2 = int(0xB8 + (0xC8 - 0xB8) * t)
            b2 = int(0xC7 + (0xD7 - 0xC7) * t)
            grad = QLinearGradient(bx, by, bx + BALL_VISIBLE, by + BALL_VISIBLE)
            grad.setColorAt(0, QColor(r1, g1, b1))
            grad.setColorAt(1, QColor(r2, g2, b2))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(bx, by, BALL_VISIBLE, BALL_VISIBLE)

        # Specular/mirror highlight (glass/jade look) on top-left of the ball
        high_g = QRadialGradient(cx - r/3, cy - r/3, r * 0.8)
        high_g.setColorAt(0.0, QColor(255, 255, 255, 110))
        high_g.setColorAt(0.4, QColor(255, 255, 255, 30))
        high_g.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(high_g))
        p.drawEllipse(int(cx - r * 0.95), int(cy - r * 0.95), int(r * 1.5), int(r * 1.5))

        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI Emoji", 32))
        p.drawText(bx, by, BALL_VISIBLE, BALL_VISIBLE, Qt.AlignmentFlag.AlignCenter, "📦")

        # Badge
        if self._count > 0:
            self._paint_badge(p, self._count, bx)

        # Status indicator dot (bottom-left of ball)
        # Status color
        if self._status == "online":
            status_color = QColor(self._theme.statusOnline)
        elif self._status == "warning":
            status_color = QColor(self._theme.statusWarning)
        elif self._status == "error":
            status_color = QColor(self._theme.statusError)
        else:
            status_color = QColor(self._theme.statusOffline)

        # Breathing animation for "warning" status
        if self._status == "warning":
            breath_alpha = int(100 + 155 * (0.5 + 0.5 * math.sin(self._breath_phase * math.pi * 2)))
            status_color = QColor(status_color.red(), status_color.green(), status_color.blue(), breath_alpha)
        dot_size = 10
        dot_x = bx + 2
        dot_y = by + BALL_VISIBLE - dot_size - 2
        p.setPen(QPen(QColor(30, 30, 30), 1))
        p.setBrush(QBrush(status_color))
        p.drawEllipse(int(dot_x), int(dot_y), dot_size, dot_size)

        p.restore()

    def _paint_badge(self, p: QPainter, count: int, ball_x: float):
        from PyQt6.QtGui import QFont
        badge_text = str(count) if count <= 99 else "99+"
        fm = p.fontMetrics()
        text_w = fm.horizontalAdvance(badge_text)
        bw = max(BADGE_W, text_w + 10)
        # 角标：球体右上角，部分重叠在球体上
        bx = ball_x + BALL_VISIBLE - bw + 4
        by = BALL_MARGIN_TOP - BADGE_H + 4

        path = QPainterPath()
        path.addRoundedRect(float(bx), float(by), float(bw), float(BADGE_H), BADGE_H / 2, BADGE_H / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0xF0, 0x64, 0x64))
        p.drawPath(path)

        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        p.drawText(bx, by, bw, BADGE_H, Qt.AlignmentFlag.AlignCenter, badge_text)

    def _paint_preview_bar(self, p: QPainter):
        from PyQt6.QtGui import QFont
        w, h = self.width(), self.height()

        # Background
        bg = QPainterPath()
        bg.addRoundedRect(QRectF(0, 0, w, h), 16, 16)
        p.setPen(QPen(QColor(self._theme.lineSoft), 1))
        p.setBrush(QColor(self._theme.surface1))
        p.drawPath(bg)

        # Vertical list items
        y = VLIST_PADDING - self._scroll_offset
        content_w = w - ACTION_AREA_W - VLIST_PADDING * 2
        for i, item in enumerate(self._items[:MAX_VISIBLE_THUMBS]):
            if y + VLIST_ITEM_H < 0:  # above visible area
                y += VLIST_ITEM_H
                continue
            if y > h:  # below visible area
                break

            row_rect = QRectF(VLIST_PADDING, y, content_w, VLIST_ITEM_H - 2)
            hovered = i == self._hovered_index

            # Row hover highlight: mint green translucent overlay
            if hovered:
                hover_bg = QPainterPath()
                hover_bg.addRoundedRect(row_rect, 8, 8)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(124, 224, 195, 18))
                p.drawPath(hover_bg)

            # Thumbnail (40x40, left side)
            thumb_rect = QRectF(VLIST_PADDING + 4, y + (VLIST_ITEM_H - VLIST_THUMB) / 2,
                                VLIST_THUMB, VLIST_THUMB)
            self._paint_thumb(p, thumb_rect, item, i)

            # Filename (right of thumbnail)
            text_x = VLIST_PADDING + VLIST_THUMB + 12
            text_w = content_w - VLIST_THUMB - 16
            p.setPen(QColor(self._theme.textPrimary))
            p.setFont(QFont("Microsoft YaHei", 10))
            filename = self._get_item_filename(item)
            fm = p.fontMetrics()
            elided = fm.elidedText(filename, Qt.TextElideMode.ElideRight, int(text_w))
            p.drawText(QRectF(text_x, y + 6, text_w, 20),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

            # Sub-info line (type + size)
            p.setPen(QColor(self._theme.textSecondary))
            p.setFont(QFont("Microsoft YaHei", 8))
            sub_info = self._get_item_subinfo(item)
            p.drawText(QRectF(text_x, y + 28, text_w, 16),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, sub_info)

            y += VLIST_ITEM_H

        # Action area (right side)
        self._paint_action_area(p, w, h)

    @staticmethod
    def _get_item_filename(item: ClipboardItem) -> str:
        """Get display filename for an item."""
        if item.file_path:
            return os.path.basename(item.file_path)
        if item.content_type == ContentType.FILES and item.content_text:
            first = item.content_text.split("\n")[0].strip()
            return os.path.basename(first)
        if item.content_type == ContentType.TEXT:
            text = (item.content_text or "")[:30].replace("\n", " ")
            return text if text else "文本"
        if item.content_type == ContentType.HTML:
            return "HTML 内容"
        if item.content_type == ContentType.IMAGE:
            return "图片"
        return "未知"

    @staticmethod
    def _get_item_subinfo(item: ClipboardItem) -> str:
        """Get sub-info line for an item (type + size)."""
        parts = []
        type_labels = {
            ContentType.TEXT: "文本", ContentType.HTML: "HTML",
            ContentType.IMAGE: "图片", ContentType.FILES: "文件",
        }
        parts.append(type_labels.get(item.content_type, ""))
        if item.content_type == ContentType.FILES and item.content_text:
            count = len(item.content_text.split("\n"))
            if count > 1:
                parts.append(f"{count} 个文件")
        if item.content_text and item.content_type == ContentType.TEXT:
            parts.append(f"{len(item.content_text)} 字符")
        return " · ".join(filter(None, parts))

    def _paint_action_area(self, p: QPainter, w: int, h: int):
        from PyQt6.QtGui import QFont
        ax = w - ACTION_AREA_W
        center = h / 2

        # ▲ expand — above center
        btn = QRectF(ax + 4, center - 30, ACTION_AREA_W - 8, 20)
        path = QPainterPath()
        path.addRoundedRect(btn, 8, 8)
        p.setPen(Qt.PenStyle.NoPen)
        if self._hovered_btn == "expand":
            p.setBrush(QColor(124, 224, 195, 40))
        else:
            p.setBrush(QColor(self._theme.bgTertiary))
        p.drawPath(path)
        p.setPen(QColor(self._theme.accentMint) if self._hovered_btn == "expand" else QColor(self._theme.textSecondary))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(btn, Qt.AlignmentFlag.AlignCenter, "▲")

        # Count — centered
        cr = QRectF(ax, center - 8, ACTION_AREA_W, 16)
        p.setPen(QColor(self._theme.textSecondary))
        p.setFont(QFont("Microsoft YaHei", 8))
        p.drawText(cr, Qt.AlignmentFlag.AlignCenter, str(len(self._items)))

        # ✕ close — below center, fully within widget bounds
        cl = QRectF(ax + 4, center + 10, ACTION_AREA_W - 8, 20)
        cp = QPainterPath()
        cp.addRoundedRect(cl, 8, 8)
        p.setPen(Qt.PenStyle.NoPen)
        if self._hovered_btn == "close":
            p.setBrush(QColor(124, 224, 195, 40))
        else:
            p.setBrush(QColor(self._theme.bgTertiary))
        p.drawPath(cp)
        p.setPen(QColor(self._theme.accentMint) if self._hovered_btn == "close" else QColor(self._theme.textSecondary))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(cl, Qt.AlignmentFlag.AlignCenter, "✕")

    def _paint_staging_grid(self, p: QPainter):
        """Paint the staging shelf as a grid of content cards."""
        from PyQt6.QtGui import QFont
        w, h = self.width(), self.height()

        # Background
        bg = QPainterPath()
        bg.addRoundedRect(QRectF(0, 0, w, h), 14, 14)
        p.setPen(QPen(QColor(self._theme.lineSoft), 1))
        p.setBrush(QColor(self._theme.surface1))
        p.drawPath(bg)

        # Header
        header_rect = QRectF(STAGING_PADDING, 4, w - STAGING_PADDING * 2, STAGING_HEADER_H)
        p.setPen(QColor(self._theme.textSecondary))
        p.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        p.drawText(header_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "📥 暂存架")
        p.setPen(QColor(self._theme.textPlaceholder))
        p.setFont(QFont("Segoe UI", 9))
        count_text = f"{len(self._staging_items)}/20"
        p.drawText(header_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, count_text)

        # Grid cards
        y_start = STAGING_HEADER_H + STAGING_PADDING
        for i, item in enumerate(self._staging_items[:STAGING_MAX_CARDS]):
            col = i % STAGING_COLS
            row = i // STAGING_COLS
            cx = STAGING_PADDING + col * (STAGING_CARD_SIZE + STAGING_GAP)
            cy = y_start + row * (STAGING_CARD_SIZE + STAGING_GAP)
            card_rect = QRectF(cx, cy, STAGING_CARD_SIZE, STAGING_CARD_SIZE)

            # Card background
            card_path = QPainterPath()
            card_path.addRoundedRect(card_rect, 8, 8)
            hovered = i == self._hovered_index
            if hovered:
                p.setPen(QPen(QColor(self._theme.borderHover), 1))
                p.setBrush(QColor(self._theme.bgHover))
            else:
                p.setPen(QPen(QColor(self._theme.border), 1))
                p.setBrush(QColor(self._theme.bgTertiary))
            p.drawPath(card_path)

            # Card content
            ct = item.get("content_type", "TEXT")
            thumb_path = item.get("thumbnail_path", "")
            file_path = item.get("file_path", "")

            if ct == "IMAGE" and thumb_path and Path(thumb_path).exists():
                # Image thumbnail
                pixmap = QPixmap(thumb_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        int(STAGING_CARD_SIZE - 8), int(STAGING_CARD_SIZE - 8),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    img_x = cx + (STAGING_CARD_SIZE - scaled.width()) / 2
                    img_y = cy + (STAGING_CARD_SIZE - scaled.height()) / 2
                    p.drawPixmap(int(img_x), int(img_y), scaled)
            else:
                # Type icon
                icon_map = {
                    "TEXT": ("📝", QColor(self._theme.typeText)),
                    "HTML": ("🌐", QColor(self._theme.accentCyan)),
                    "FILES": ("📄", QColor(self._theme.typeWord)),
                }
                icon, color = icon_map.get(ct, ("📋", QColor(self._theme.typeText)))

                # Check file extension for specific icons
                if ct == "FILES" and item.get("content_text"):
                    first = item["content_text"].split("\n")[0].strip()
                    ext = Path(first).suffix.lower() if first else ""
                    ext_icons = {
                        ".pdf": ("📕", QColor(self._theme.typePdf)),
                        ".doc": ("📘", QColor(self._theme.typeWord)),
                        ".docx": ("📘", QColor(self._theme.typeWord)),
                        ".xls": ("📗", QColor(self._theme.typeExcel)),
                        ".xlsx": ("📗", QColor(self._theme.typeExcel)),
                        ".ppt": ("📙", QColor(self._theme.typePpt)),
                        ".pptx": ("📙", QColor(self._theme.typePpt)),
                    }
                    if ext in ext_icons:
                        icon, color = ext_icons[ext]

                p.setFont(QFont("Segoe UI Emoji", 22))
                p.setPen(QColor(255, 255, 255))
                icon_rect = QRectF(cx, cy, STAGING_CARD_SIZE, STAGING_CARD_SIZE - 16)
                p.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, icon)

                # Title text
                title = self._staging_card_title(item)
                p.setFont(QFont("Microsoft YaHei", 7))
                p.setPen(QColor(self._theme.textTertiary))
                title_rect = QRectF(cx + 2, cy + STAGING_CARD_SIZE - 18, STAGING_CARD_SIZE - 4, 14)
                p.drawText(title_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, title)

            # Drag-over highlight on card
            if self._drag_over and hovered:
                overlay = QPainterPath()
                overlay.addRoundedRect(card_rect, 8, 8)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(124, 224, 195, 40))
                p.drawPath(overlay)

        # Empty state
        if not self._staging_items:
            empty_rect = QRectF(STAGING_PADDING, y_start, w - STAGING_PADDING * 2, STAGING_CARD_SIZE)
            p.setPen(QColor(self._theme.textPlaceholder))
            p.setFont(QFont("Microsoft YaHei", 10))
            p.drawText(empty_rect, Qt.AlignmentFlag.AlignCenter, "拖入文件到此处")

        # Drop zone indicator (when dragging over)
        if self._drag_over:
            # Highlight the whole staging area
            drop_zone = QPainterPath()
            drop_zone.addRoundedRect(QRectF(STAGING_PADDING, y_start,
                w - STAGING_PADDING * 2,
                max(STAGING_CARD_SIZE, h - y_start - STAGING_FOOTER_H)), 8, 8)
            p.setPen(QPen(QColor(self._theme.accentMint), 2, Qt.PenStyle.DashLine))
            p.setBrush(QColor(124, 224, 195, 15))
            p.drawPath(drop_zone)

    @staticmethod
    def _staging_card_title(item: dict) -> str:
        """Generate a short title for a staging card."""
        ct = item.get("content_type", "TEXT")
        if ct == "TEXT":
            text = (item.get("content_text") or "")[:12].replace("\n", " ")
            return text or "文本"
        if ct == "IMAGE":
            return "图片"
        if ct == "FILES":
            fp = (item.get("content_text") or "").split("\n")[0].strip()
            return Path(fp).name[:12] if fp else "文件"
        if ct == "HTML":
            return "HTML"
        return "内容"

    def _paint_thumb(self, p: QPainter, rect: QRectF, item: ClipboardItem, index: int):
        hovered = index == self._hovered_index
        dragging = index == self._dragging_index

        if hovered and not dragging:
            rect = rect.translated(0, -2)

        tp = QPainterPath()
        tp.addRoundedRect(rect, 10, 10)

        if dragging:
            p.setOpacity(0.3)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 15))
        p.drawPath(tp)

        # Content
        if item.content_type == ContentType.IMAGE and item.thumbnail_path:
            pix = QPixmap(item.thumbnail_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    int(rect.width()), int(rect.height()),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                p.save()
                p.setClipPath(tp)
                p.drawPixmap(rect.toRect(), scaled)
                p.restore()
        elif item.content_type == ContentType.TEXT and item.content_text:
            p.setPen(QColor(178, 190, 195))
            from PyQt6.QtGui import QFont
            p.setFont(QFont("Microsoft YaHei", 8))
            p.drawText(
                rect.adjusted(4, 4, -4, -4),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                item.content_text[:40],
            )
        else:
            p.setPen(QColor(255, 255, 255))
            from PyQt6.QtGui import QFont
            p.setFont(QFont("Segoe UI Emoji", 18))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "📄")
            ext = ""
            if item.content_type == ContentType.FILES and item.content_text:
                ext = os.path.splitext(item.content_text.split("\n")[0])[1].upper().lstrip(".")
            if ext:
                p.setFont(QFont("Microsoft YaHei", 7))
                p.setPen(QColor(99, 110, 114))
                p.drawText(
                    QRectF(rect.left(), rect.bottom() - 14, rect.width(), 12),
                    Qt.AlignmentFlag.AlignCenter, ext,
                )

        # Index number
        p.setOpacity(1.0)
        p.setPen(QColor(255, 255, 255, 128))
        from PyQt6.QtGui import QFont
        p.setFont(QFont("Microsoft YaHei", 7))
        p.drawText(QRectF(rect.left() + 2, rect.top() + 1, 14, 12), Qt.AlignmentFlag.AlignCenter, str(index + 1))

        # Hover highlight
        if hovered and not dragging:
            hp = QPainterPath()
            hp.addRoundedRect(rect.adjusted(-1, -1, 1, 1), 9, 9)
            p.setBrush(Qt.BrushStyle.NoBrush)
            color = QColor(self._theme.accentMint)
            color.setAlpha(180)
            p.setPen(QPen(color, 2))
            p.drawPath(hp)

        p.setOpacity(1.0)

    # ── Mouse events ──

    def enterEvent(self, event):
        self._hovered = True
        self._hover_timer.start()
        # Long hover: ball → preview expansion (only if not dragging)
        if self._mode == "ball" and self._items and not self._is_dragging_ball:
            self._long_hover_timer.start()
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self._hovered_index = -1
        self._hovered_btn = ""
        self._hover_timer.start()
        self._long_hover_timer.stop()
        self.update()

    def _on_long_hover(self):
        """Ball long hover → morph to preview."""
        if self._mode == "ball" and self._items:
            self._morph_to_preview()

    def mousePressEvent(self, event):
        if self._is_animating:
            return
        pos = event.position()

        if self._mode == "ball":
            # Right-click on ball → context menu
            if event.button() == Qt.MouseButton.RightButton:
                self._show_ball_context_menu(event.globalPosition().toPoint())
                return
            # Left-click on ball → drag or click
            if event.button() == Qt.MouseButton.LeftButton:
                cx = BALL_MARGIN_SIDE + BALL_VISIBLE / 2
                cy = BALL_MARGIN_TOP + BALL_VISIBLE / 2
                r = BALL_VISIBLE / 2
                dx, dy = pos.x() - cx, pos.y() - cy
                if dx * dx + dy * dy <= r * r:
                    self._ball_drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    self._is_dragging_ball = True
                    self._pressed = True
                    self.update()
            return

        # Staging mode: handle card clicks
        if self._mode == "staging":
            if event.button() == Qt.MouseButton.RightButton:
                idx = self._staging_card_at(pos)
                if idx >= 0 and idx < len(self._staging_items):
                    self._show_staging_context_menu(event.globalPosition().toPoint(), idx)
                return
            if event.button() == Qt.MouseButton.LeftButton:
                idx = self._staging_card_at(pos)
                if idx >= 0 and idx < len(self._staging_items):
                    # Prepare for potential drag
                    self._drag_start_pos = event.pos()
                    self._drag_start_index = idx
                return

        # Preview mode: right-click on thumbnail
        if event.button() == Qt.MouseButton.RightButton:
            idx = self._thumb_at(pos)
            if idx >= 0 and idx < len(self._items):
                self._show_thumb_context_menu(event.globalPosition().toPoint(), idx)
            return

        # Preview mode: left-click on action area
        if event.button() == Qt.MouseButton.LeftButton:
            if pos.x() >= self.width() - ACTION_AREA_W:
                center = self.height() / 2
                if pos.y() < center - 5:
                    self.expand_requested.emit()
                elif pos.y() > center + 5:
                    # Close/preview bar → morph back to ball
                    self.clear()
                return

            self._drag_start_pos = event.pos()
            self._drag_start_index = self._thumb_at(pos)

    def mouseMoveEvent(self, event):
        # Ball reposition
        if self._mode == "ball" and self._ball_drag_pos:
            if event.buttons() & Qt.MouseButton.LeftButton:
                new_pos = event.globalPosition().toPoint() - self._ball_drag_pos
                # Edge snap
                new_pos = self._apply_edge_snap(new_pos)
                self.move(new_pos)
            return

        if self._mode == "ball":
            return

        # Staging mode: hover tracking + drag detection
        if self._mode == "staging":
            idx = self._staging_card_at(pos)
            if idx != self._hovered_index:
                self._hovered_index = idx
                self.update()
            # Drag detection for staging cards
            if self._drag_start_pos is not None and self._drag_start_index >= 0:
                distance = (event.pos() - self._drag_start_pos).manhattanLength()
                if distance > 8:
                    staging_item = self._staging_items[self._drag_start_index]
                    self._drag_start_pos = None
                    from src.ui.drag_handler import DragHandler
                    DragHandler.start_staging_drag(staging_item, self)
                    self._drag_start_index = -1
            return

        # Preview: hover tracking
        pos = event.position()

        # Track action area buttons hover
        hovered_btn = ""
        if pos.x() >= self.width() - ACTION_AREA_W:
            center = self.height() / 2
            if pos.y() < center - 5:
                hovered_btn = "expand"
            elif pos.y() > center + 5:
                hovered_btn = "close"

        if hovered_btn != self._hovered_btn:
            self._hovered_btn = hovered_btn
            self.update()

        idx = self._thumb_at(pos)
        if idx != self._hovered_index:
            self._hovered_index = idx
            self.update()

        # Drag detection
        if self._drag_start_pos and self._drag_start_index >= 0:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance > 8:
                item = self._items[self._drag_start_index]
                self._dragging_index = self._drag_start_index
                self.update()
                DragHandler.start_drag(item, self)
                self.remove_item(item)
                self._dragging_index = -1
                self._drag_start_pos = None
                self._drag_start_index = -1

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        was_dragging = self._ball_drag_pos is not None
        if self._mode == "ball" and was_dragging:
            moved = (event.globalPosition().toPoint() - self.frameGeometry().topLeft() - self._ball_drag_pos)
            if moved.manhattanLength() < 5:
                # Single click on ball: morph to preview if items exist
                if self._items:
                    self._morph_to_preview()
                else:
                    self.clicked.emit()
            self._ball_drag_pos = None
            self._is_dragging_ball = False
            self._save_position()
            return
        self._drag_start_pos = None
        self._drag_start_index = -1

        # Staging mode: click (not drag) → copy to clipboard
        if self._mode == "staging":
            pos = event.position()
            idx = self._staging_card_at(pos)
            if idx >= 0 and idx < len(self._staging_items):
                staging_id = self._staging_items[idx].get("id")
                if staging_id:
                    self.copy_item_requested.emit(staging_id)

    def mouseDoubleClickEvent(self, event):
        if self._mode == "ball":
            self.panel_show_requested.emit()
            return
        if self._mode == "staging":
            # Double-click staging card → open file if applicable
            idx = self._staging_card_at(event.position())
            if idx >= 0 and idx < len(self._staging_items):
                fp = self._staging_items[idx].get("file_path", "")
                if fp and os.path.exists(fp):
                    os.startfile(fp)
            return
        idx = self._thumb_at(event.position())
        if idx >= 0 and idx < len(self._items):
            item = self._items[idx]
            if item.file_path and os.path.exists(item.file_path):
                os.startfile(item.file_path)

    def wheelEvent(self, event):
        if self._mode != "preview":
            return
        delta = event.angleDelta().y()
        self._scroll_offset = max(0, self._scroll_offset - delta // 2)
        max_scroll = max(0,
            len(self._items) * VLIST_ITEM_H
            - self.height() + VLIST_PADDING * 2,
        )
        self._scroll_offset = min(self._scroll_offset, max_scroll)
        self.update()

    # ── Drag-drop (files into ball/bar) ──

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            self._drag_over = True
            self._ring_phase = 0.0
            # Morph to staging shelf if in ball mode
            if self._mode == "ball" and not self._is_animating:
                self._morph_to_staging()
            elif self._mode == "staging":
                self.update()
            else:
                self._ring_timer.start(33)

    def dragLeaveEvent(self, event):
        self._drag_over = False
        self._ring_timer.stop()
        # Auto-collapse staging after a short delay
        if self._mode == "staging" and not self._is_animating:
            QTimer.singleShot(800, self._maybe_collapse_staging)
        self.update()

    def _maybe_collapse_staging(self):
        """Collapse staging back to ball if drag is no longer over."""
        if not self._drag_over and self._mode == "staging" and not self._is_animating:
            self._morph_to_ball()

    def dropEvent(self, event):
        was_staging = self._mode == "staging"
        self._drag_over = False
        self._ring_timer.stop()
        # Success flash
        self._flash_active = True
        self._flash_timer.start(400)
        self.update()
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            if paths:
                if was_staging:
                    self.staging_file_dropped.emit(paths)
                else:
                    self.files_dropped.emit(paths)
            event.acceptProposedAction()
        elif event.mimeData().hasText():
            # Text content dropped → add to staging
            if was_staging:
                text = event.mimeData().text()
                if text:
                    self.staging_file_dropped.emit([text])
            event.acceptProposedAction()

    # ── Context menus ──

    def _show_ball_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #10161C; border: 1px solid rgba(255,255,255,0.08);"
            " color: #F0F5F2; padding: 4px; border-radius: 12px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 6px; }"
            "QMenu::item:selected { background: rgba(124,224,195,0.15); color: #7CE0C3; }"
        )
        menu.addAction("显示面板").triggered.connect(self.panel_show_requested.emit)
        menu.addAction("隐藏悬浮球").triggered.connect(self.hide_ball_requested.emit)
        menu.addSeparator()
        menu.addAction("暂停/开启剪贴板监听").triggered.connect(self.toggle_monitoring_requested.emit)
        menu.addSeparator()
        menu.addAction("退出").triggered.connect(self.quit_requested.emit)
        menu.exec(global_pos)

    def _show_thumb_context_menu(self, global_pos, index: int):
        if index < 0 or index >= len(self._items):
            return
        item = self._items[index]
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #10161C; border: 1px solid rgba(255,255,255,0.08);"
            " color: #F0F5F2; padding: 4px; border-radius: 12px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 6px; }"
            "QMenu::item:selected { background: rgba(124,224,195,0.15); color: #7CE0C3; }"
        )
        menu.addAction("复制").triggered.connect(lambda: self.copy_item_requested.emit(item.id))
        menu.addAction("预览").triggered.connect(lambda: self.preview_item_requested.emit(item))
        if item.file_path and os.path.exists(item.file_path):
            menu.addAction("用默认程序打开").triggered.connect(lambda: os.startfile(item.file_path))
        menu.addSeparator()
        menu.addAction("从预览栏移除").triggered.connect(lambda: self._remove_thumb(index))
        menu.exec(global_pos)

    def _remove_thumb(self, index: int):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.remove_item_requested.emit(item.id)
            if not self._items:
                self._morph_to_ball()
            else:
                self.update()

    # ── Helpers ──

    def _thumb_at(self, pos: QPointF) -> int:
        """Hit test: return item index at pos, or -1. Uses vertical list layout."""
        if self._mode != "preview":
            return -1
        content_w = self.width() - ACTION_AREA_W - VLIST_PADDING * 2
        y = VLIST_PADDING - self._scroll_offset
        for i in range(min(len(self._items), MAX_VISIBLE_THUMBS)):
            row_rect = QRectF(VLIST_PADDING, y, content_w, VLIST_ITEM_H - 2)
            if row_rect.contains(pos):
                return i
            y += VLIST_ITEM_H
        return -1

    def _staging_card_at(self, pos: QPointF) -> int:
        """Hit test: return staging card index at pos, or -1."""
        if self._mode != "staging":
            return -1
        y_start = STAGING_HEADER_H + STAGING_PADDING
        for i in range(len(self._staging_items[:STAGING_MAX_CARDS])):
            col = i % STAGING_COLS
            row = i // STAGING_COLS
            cx = STAGING_PADDING + col * (STAGING_CARD_SIZE + STAGING_GAP)
            cy = y_start + row * (STAGING_CARD_SIZE + STAGING_GAP)
            card_rect = QRectF(cx, cy, STAGING_CARD_SIZE, STAGING_CARD_SIZE)
            if card_rect.contains(pos):
                return i
        return -1

    def _show_staging_context_menu(self, global_pos, index: int):
        """Show context menu for a staging card."""
        if index >= len(self._staging_items):
            return
        item = self._staging_items[index]
        staging_id = item.get("id")
        if not staging_id:
            return

        menu = QMenu(self)
        copy_action = menu.addAction("📋 复制到剪贴板")
        history_action = menu.addAction("📤 存回历史")
        menu.addSeparator()
        remove_action = menu.addAction("🗑 移除")

        action = menu.exec(global_pos)
        if action == copy_action:
            self.copy_item_requested.emit(staging_id)
        elif action == history_action:
            self.remove_item_requested.emit(staging_id)
        elif action == remove_action:
            self.remove_item_requested.emit(staging_id)

    def _apply_edge_snap(self, pos: QPoint) -> QPoint:
        screen = QApplication.primaryScreen()
        if not screen:
            return pos
        geo = screen.availableGeometry()
        SNAP = 20
        x, y = pos.x(), pos.y()
        if abs(x - geo.left()) < SNAP:
            x = geo.left() + 8
        elif abs(geo.right() - (x + BALL_WINDOW_W)) < SNAP:
            x = geo.right() - BALL_WINDOW_W - 8
        if abs(y - geo.top()) < SNAP:
            y = geo.top() + 8
        elif abs(geo.bottom() - (y + BALL_WINDOW_H)) < SNAP:
            y = geo.bottom() - BALL_WINDOW_H - 8
        return QPoint(x, y)

    def _save_position(self):
        try:
            from src.core.config import Config
            cfg = Config()
            cfg.set_ball_position(self.x(), self.y())
        except Exception:
            pass
