"""Windows clipboard listener using Win32 hidden window + WM_CLIPBOARDUPDATE."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
from typing import Callable, Optional

import win32clipboard
import win32con
import win32gui

# Win32 消息常量
WM_CLIPBOARDUPDATE = 0x031D

user32 = ctypes.windll.user32


class ClipboardListener:
    """Listens for system clipboard changes via a hidden Win32 window.

    Runs its own message pump in a QThread. Emits a callback on each change.
    """

    def __init__(self, on_change: Callable[[], None]):
        self._on_change = on_change
        self._hwnd: Optional[int] = None
        self._running = False

    def start(self) -> None:
        """Create hidden window and start message pump. Call from a QThread."""
        # 创建隐藏窗口
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = "ElevenListener"
        wc.hInstance = win32gui.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        self._hwnd = win32gui.CreateWindow(
            class_atom, "ElevenListener", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
        )
        # 注册剪贴板监听
        user32.AddClipboardFormatListener(self._hwnd)
        self._running = True
        # 消息泵 - 阻塞直到 WM_QUIT
        win32gui.PumpMessages()

    def stop(self) -> None:
        """Stop the listener and destroy the hidden window."""
        if self._hwnd:
            user32.RemoveClipboardFormatListener(self._hwnd)
            win32gui.PostMessage(self._hwnd, win32con.WM_QUIT, 0, 0)
            self._running = False

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_CLIPBOARDUPDATE:
            try:
                self._on_change()
            except Exception:
                pass  # 不要让回调异常崩溃消息泵
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


def get_clipboard_text() -> Optional[str]:
    """Read plain text from clipboard. Returns None if not text."""
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        return None
    except Exception:
        return None
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def get_clipboard_files() -> Optional[list[str]]:
    """Read file list from clipboard. Returns None if not files."""
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
            import win32con as wc
            data = win32clipboard.GetClipboardData(wc.CF_HDROP)
            return list(data)
        return None
    except Exception:
        return None
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def get_clipboard_image() -> Optional[bytes]:
    """Read image from clipboard as DIB bytes. Returns None if not image."""
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
            return win32clipboard.GetClipboardData(win32con.CF_DIB)
        return None
    except Exception:
        return None
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def get_clipboard_html() -> Optional[str]:
    """Read HTML content from clipboard. Returns None if not HTML."""
    try:
        win32clipboard.OpenClipboard()
        # 注册 HTML Format 剪贴板格式
        html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
        if win32clipboard.IsClipboardFormatAvailable(html_format):
            data = win32clipboard.GetClipboardData(html_format)
            if isinstance(data, bytes):
                # HTML Format 是 UTF-8 编码的 CF_HTML 格式
                # 需要解析头部获取片段
                return _parse_cf_html(data)
            return None
        return None
    except Exception:
        return None
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def _parse_cf_html(data: bytes) -> Optional[str]:
    """Parse CF_HTML format and extract the HTML fragment."""
    try:
        # CF_HTML 格式: Version:0.9\r\nStartHTML:xxx\r\nEndHTML:xxx\r\n...
        header_end = data.find(b"<!--")
        if header_end == -1:
            return None

        header = data[:header_end].decode("ascii", errors="ignore")

        # 提取 StartHTML 和 EndHTML
        import re
        start_match = re.search(r"StartHTML:(\d+)", header)
        end_match = re.search(r"EndHTML:(\d+)", header)

        if not start_match or not end_match:
            return None

        start = int(start_match.group(1))
        end = int(end_match.group(1))

        # 提取 HTML 片段
        html_fragment = data[start:end].decode("utf-8", errors="ignore")
        return html_fragment
    except Exception:
        return None


def set_clipboard_text(text: str) -> None:
    """Write plain text to clipboard."""
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def set_clipboard_files(files: list[str]) -> None:
    """Write file list to clipboard as CF_HDROP."""
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        # 构造 DROPFILES 结构
        import struct
        import ctypes

        # DROPFILES 结构: 20 字节头 + 双 null 结尾的文件列表
        files_str = "\0".join(files) + "\0\0"
        files_bytes = files_str.encode("utf-16-le")

        # DROPFILES: pFiles(4), pt(8), fNC(4), fWide(4) = 20 bytes
        dropfiles = struct.pack("Iiiii", 20, 0, 0, 0, 1)  # fWide=1 表示 Unicode
        data = dropfiles + files_bytes

        win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
    finally:
        win32clipboard.CloseClipboard()
