"""Toggleable tag chip widget for the filter bar."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QPushButton

from src.ui.design_system import Palette, Fonts, Spacing, Radius


def _brighten(hex_color: str, factor: float = 0.25) -> str:
    """Return a brighter version of the given hex color."""
    c = QColor(hex_color)
    h, s, l_val, a = c.getHslF()
    l_val = min(1.0, l_val + factor)
    c.setHslF(h, s, l_val, a)
    return c.name()


class TagChip(QPushButton):
    """A toggleable pill-shaped chip representing a tag."""

    tag_clicked = pyqtSignal(int, bool)  # (tag_id, is_selected)

    def __init__(self, tag_id: int, name: str, color: str, parent=None):
        super().__init__(name, parent)
        self.tag_id = tag_id
        self._color = color
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(checked=False)
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        self._update_style(checked)
        self.tag_clicked.emit(self.tag_id, checked)

    def _update_style(self, checked: bool) -> None:
        bg = _brighten(self._color, 0.20) if checked else self._color
        border = f"1px solid {Palette.BORDER}" if checked else "1px solid transparent"
        self.setStyleSheet(
            f"QPushButton {{"
            f"  background: {bg};"
            f"  color: {Palette.TEXT_PRIMARY};"
            f"  border: {border};"
            f"  border-radius: {Radius.FULL}px;"
            f"  padding: {Spacing.XS}px {Spacing.MD}px;"
            f"  font-family: {Fonts.FAMILY_PRIMARY};"
            f"  font-size: {Fonts.SIZE_MD}px;"
            f"  font-weight: {'bold' if checked else 'normal'};"
            f"}}"
        )
