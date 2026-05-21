"""Windows global hotkey using RegisterHotKey + QAbstractNativeEventFilter."""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
from typing import Callable

from PyQt6.QtCore import QAbstractNativeEventFilter, pyqtBoundSignal

logger = logging.getLogger(__name__)

# Windows constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


class _NativeHotkeyFilter(QAbstractNativeEventFilter):
    """Listens for WM_HOTKEY messages dispatched by Windows."""

    def __init__(self) -> None:
        super().__init__()
        self._handlers: dict[int, Callable[[], None]] = {}

    def register(self, hotkey_id: int, callback: Callable[[], None]) -> None:
        self._handlers[hotkey_id] = callback

    def unregister(self, hotkey_id: int) -> None:
        self._handlers.pop(hotkey_id, None)

    def nativeEventFilter(self, eventType: bytes, message: int) -> tuple[bool, int]:
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                handler = self._handlers.get(msg.wParam)
                if handler:
                    try:
                        handler()
                    except Exception:
                        logger.exception("Global hotkey handler error")
                    return True, 0
        return False, 0


# Singleton filter — installed once per process
_filter: _NativeHotkeyFilter | None = None
_next_id = 1


def _ensure_filter() -> _NativeHotkeyFilter:
    global _filter
    if _filter is None:
        _filter = _NativeHotkeyFilter()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().installNativeEventFilter(_filter)
    return _filter


def register_hotkey(modifiers: int, vk: int, callback: Callable[[], None]) -> int:
    """Register a system-wide hotkey. Returns the hotkey ID for unregistering.

    Args:
        modifiers: Combination of MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT.
        vk: Virtual-key code (e.g. ord('V') for the V key).
        callback: Function to call when the hotkey is pressed.

    Returns:
        Hotkey ID used to unregister later.
    """
    global _next_id
    f = _ensure_filter()
    hotkey_id = _next_id
    _next_id += 1

    if not ctypes.windll.user32.RegisterHotKey(None, hotkey_id, modifiers, vk):
        err = ctypes.get_last_error()
        logger.error("RegisterHotKey failed for id=%d, vk=%d, error=%d", hotkey_id, vk, err)
        raise OSError(f"RegisterHotKey failed (error {err})")

    f.register(hotkey_id, callback)
    logger.info("Registered global hotkey id=%d, modifiers=0x%x, vk=0x%x", hotkey_id, modifiers, vk)
    return hotkey_id


def unregister_hotkey(hotkey_id: int) -> None:
    """Unregister a previously registered hotkey."""
    ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
    if _filter:
        _filter.unregister(hotkey_id)
    logger.info("Unregistered global hotkey id=%d", hotkey_id)


def unregister_all() -> None:
    """Unregister all hotkeys registered by this module."""
    if _filter:
        for hid in list(_filter._handlers.keys()):
            unregister_hotkey(hid)
