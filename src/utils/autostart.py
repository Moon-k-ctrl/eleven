"""Auto-start on Windows boot."""
from __future__ import annotations

import sys
import winreg

APP_NAME = "Eleven"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_autostart_enabled() -> bool:
    """Check if auto-start is enabled."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    """Enable or disable auto-start on boot.

    Returns True if successful.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                # 获取当前可执行文件路径
                exe_path = sys.executable
                if getattr(sys, 'frozen', None):
                    # PyInstaller 打包后的路径
                    exe_path = sys.executable
                else:
                    # 开发模式：使用 python -m src.main
                    exe_path = f'"{exe_path}" -m src.main'

                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
