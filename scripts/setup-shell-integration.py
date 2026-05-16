"""Windows shell integration for 拾遗 (eleven).

Registers:
  - SendTo shortcut: %APPDATA%\\Microsoft\\Windows\\SendTo\\拾遗.lnk
  - Context menu:    HKCU\\Software\\Classes\\*\\shell\\拾遗
  - Directory menu:  HKCU\\Software\\Classes\\Directory\\shell\\拾遗

Usage:
  python scripts/setup-shell-integration.py install [--exe PATH]
  python scripts/setup-shell-integration.py uninstall
"""
from __future__ import annotations

import argparse
import os
import sys
import winreg

# ── Constants ──

APP_NAME = "拾遗"
REG_BASE = r"Software\Classes"
SEND_TO_DIR = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "SendTo")


def _get_exe_path(exe_override: str | None = None) -> str:
    """Resolve the exe path for shortcuts/registry."""
    if exe_override:
        return exe_override
    # Try dist output
    dist_exe = os.path.join(os.path.dirname(__file__), "..", "dist", "eleven", "eleven.exe")
    if os.path.isfile(dist_exe):
        return os.path.abspath(dist_exe)
    # Fallback to python -m
    return sys.executable


def _reg_add(hive: int, subkey: str, name: str, value: str) -> None:
    """Add or overwrite a registry string value."""
    key = winreg.CreateKeyEx(hive, subkey, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    winreg.CloseKey(key)


def _reg_delete_tree(hive: int, subkey: str) -> None:
    """Delete a registry key tree (best-effort)."""
    try:
        winreg.DeleteKey(hive, subkey)
    except OSError:
        # Key has subkeys; delete them first
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_ALL_ACCESS)
            subkeys = []
            i = 0
            while True:
                try:
                    subkeys.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
            for sk in subkeys:
                _reg_delete_tree(hive, f"{subkey}\\{sk}")
            winreg.DeleteKey(hive, subkey)
        except OSError:
            pass


# ── Install ──

def install(exe_path: str | None = None) -> None:
    exe = _get_exe_path(exe_path)
    print(f"Using exe: {exe}")

    # 1. SendTo shortcut
    try:
        import win32com.client
        os.makedirs(SEND_TO_DIR, exist_ok=True)
        shortcut_path = os.path.join(SEND_TO_DIR, f"{APP_NAME}.lnk")
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = exe
        shortcut.Arguments = "--add"
        shortcut.WorkingDirectory = os.path.dirname(exe)
        shortcut.Description = f"发送到{APP_NAME}"
        shortcut.save()
        print(f"SendTo shortcut: {shortcut_path}")
    except ImportError:
        print("WARNING: pywin32 not installed, skipping SendTo shortcut")
    except Exception as e:
        print(f"WARNING: SendTo shortcut failed: {e}")

    # 2. Context menu (files)
    file_key = rf"{REG_BASE}\*\shell\{APP_NAME}"
    _reg_add(winreg.HKEY_CURRENT_USER, file_key, "", f"发送到 {APP_NAME}")
    _reg_add(winreg.HKEY_CURRENT_USER, file_key, "Icon", exe)
    _reg_add(winreg.HKEY_CURRENT_USER, rf"{file_key}\command", "", f'"{exe}" --add "%1"')
    print(f"Context menu (files): HKCU\\{file_key}")

    # 3. Context menu (directories)
    dir_key = rf"{REG_BASE}\Directory\shell\{APP_NAME}"
    _reg_add(winreg.HKEY_CURRENT_USER, dir_key, "", f"发送到 {APP_NAME}")
    _reg_add(winreg.HKEY_CURRENT_USER, dir_key, "Icon", exe)
    _reg_add(winreg.HKEY_CURRENT_USER, rf"{dir_key}\command", "", f'"{exe}" --add "%1"')
    print(f"Context menu (dirs): HKCU\\{dir_key}")

    print("Shell integration installed.")


# ── Uninstall ──

def uninstall() -> None:
    # 1. Remove SendTo shortcut
    shortcut_path = os.path.join(SEND_TO_DIR, f"{APP_NAME}.lnk")
    if os.path.isfile(shortcut_path):
        os.remove(shortcut_path)
        print(f"Removed SendTo shortcut: {shortcut_path}")

    # 2. Remove context menu entries
    for sub in [r"*\shell", r"Directory\shell"]:
        key_path = rf"{REG_BASE}\{sub}\{APP_NAME}"
        _reg_delete_tree(winreg.HKEY_CURRENT_USER, key_path)
        print(f"Removed: HKCU\\{key_path}")

    print("Shell integration uninstalled.")


# ── CLI ──

def main() -> None:
    parser = argparse.ArgumentParser(description="拾遗 shell integration setup")
    sub = parser.add_subparsers(dest="command")

    p_install = sub.add_parser("install", help="Register shell integration")
    p_install.add_argument("--exe", help="Path to eleven executable")

    sub.add_parser("uninstall", help="Remove shell integration")

    args = parser.parse_args()
    if args.command == "install":
        install(getattr(args, "exe", None))
    elif args.command == "uninstall":
        uninstall()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
