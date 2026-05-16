"""Acrylic/glass effect for Windows 10/11."""
from __future__ import annotations

import ctypes
import sys
from typing import Optional

from PyQt6.QtWidgets import QWidget

# Windows API constants
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWA_MICA_EFFECT = 1029

# Backdrop types
DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2  # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic
DWMSBT_TABBEDWINDOW = 4  # Tabbed Mica

dwmapi = ctypes.windll.dwmapi


def _get_windows_build() -> int:
    """Get Windows build number."""
    try:
        return sys.getwindowsversion().build
    except Exception:
        return 0


def enable_acrylic(widget: QWidget, fallback_color: str = "rgba(30, 30, 30, 0.95)") -> bool:
    """Enable acrylic/glass effect on a widget.

    Returns True if a native effect was applied.
    """
    hwnd = int(widget.winId())
    build = _get_windows_build()

    if build >= 22000:
        # Windows 11: Try Mica
        return _enable_mica(hwnd)
    elif build >= 17763:
        # Windows 10 1809+: Try Acrylic
        return _enable_acrylic_win10(hwnd)

    return False


def _enable_mica(hwnd: int) -> bool:
    """Enable Mica effect on Windows 11."""
    try:
        # Enable dark mode
        value = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value), ctypes.sizeof(value)
        )

        # Set backdrop type to Mica
        value = ctypes.c_int(DWMSBT_MAINWINDOW)
        result = dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(value), ctypes.sizeof(value)
        )
        return result == 0
    except Exception:
        return False


def _enable_acrylic_win10(hwnd: int) -> bool:
    """Enable Acrylic effect on Windows 10."""
    try:
        # Enable dark mode
        value = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value), ctypes.sizeof(value)
        )

        # Set backdrop type to Acrylic
        value = ctypes.c_int(DWMSBT_TRANSIENTWINDOW)
        result = dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(value), ctypes.sizeof(value)
        )
        return result == 0
    except Exception:
        return False


def disable_acrylic(widget: QWidget) -> None:
    """Disable acrylic/glass effect."""
    hwnd = int(widget.winId())
    try:
        value = ctypes.c_int(DWMSBT_NONE)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass
