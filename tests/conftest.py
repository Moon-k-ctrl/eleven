"""Shared fixtures and Win32 mocks for eleven test suite."""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ── Win32 Module Mocks ──
# Must happen BEFORE any src.* imports that depend on win32 modules.

def _ensure_win32_mock() -> None:
    """Install mock win32 modules into sys.modules if the real ones are absent."""
    mock_modules = [
        "win32clipboard", "win32con", "win32gui", "win32api",
        "win32.lib", "win32.lib.pywintypes",
        "pywintypes",
    ]
    for mod_name in mock_modules:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    # win32clipboard helpers
    wb = sys.modules["win32clipboard"]
    wb.OpenClipboard = MagicMock()
    wb.CloseClipboard = MagicMock()
    wb.EmptyClipboard = MagicMock()
    wb.GetClipboardData = MagicMock(return_value=None)
    wb.SetClipboardData = MagicMock()
    wb.IsClipboardFormatAvailable = MagicMock(return_value=False)
    wb.EnumClipboardFormats = MagicMock(return_value=[])
    wb.RegisterClipboardFormat = MagicMock(return_value=0xC001)

    # win32con constants
    wc = sys.modules["win32con"]
    wc.CF_UNICODETEXT = 13
    wc.CF_HDROP = 15
    wc.CF_DIB = 8
    wc.WM_QUIT = 0x0012

    # win32gui
    wg = sys.modules["win32gui"]
    wg.WNDCLASS = MagicMock
    wg.GetModuleHandle = MagicMock(return_value=0)
    wg.RegisterClass = MagicMock(return_value=1)
    wg.CreateWindow = MagicMock(return_value=1)
    wg.PumpMessages = MagicMock()
    wg.PostMessage = MagicMock()
    wg.DefWindowProc = MagicMock(return_value=0)

    # win32api
    wa = sys.modules["win32api"]
    wa.RegisterWindowMessage = MagicMock(return_value=0x1234)
    wa.GetMessage = MagicMock(return_value=(0, 0, 0))

    # PyQt6 — mock if not installed (headless CI)
    if "PyQt6" not in sys.modules:
        _mock_pyqt6()


def _mock_pyqt6() -> None:
    """Install minimal PyQt6 mocks for headless environments."""
    qt_core = types.ModuleType("PyQt6.QtCore")

    class _FakeSignal:
        def __init__(self, *args, **kwargs):
            pass
        def connect(self, *a, **kw):
            pass
        def disconnect(self, *a, **kw):
            pass
        def emit(self, *a, **kw):
            pass

    class _FakeQObject:
        def __init__(self, *args, **kwargs):
            pass

    qt_core.QObject = _FakeQObject
    qt_core.pyqtSignal = lambda *a, **kw: _FakeSignal()
    qt_core.QThread = _FakeQObject

    sys.modules["PyQt6"] = types.ModuleType("PyQt6")
    sys.modules["PyQt6.QtCore"] = qt_core
    sys.modules["PyQt6.QtWidgets"] = types.ModuleType("PyQt6.QtWidgets")
    sys.modules["PyQt6.QtGui"] = types.ModuleType("PyQt6.QtGui")

    # QtWidgets stubs
    qw = sys.modules["PyQt6.QtWidgets"]
    qw.QApplication = MagicMock()
    qw.QSystemTrayIcon = MagicMock()
    qw.QMenu = MagicMock()
    qw.QAction = MagicMock()
    qw.QWidget = _FakeQObject
    qw.QVBoxLayout = MagicMock
    qw.QHBoxLayout = MagicMock
    qw.QLabel = MagicMock
    qw.QPushButton = MagicMock
    qw.QScrollArea = MagicMock
    qw.QGraphicsDropShadowEffect = MagicMock

    # QtGui stubs
    qg = sys.modules["PyQt6.QtGui"]
    qg.QIcon = MagicMock
    qg.QPixmap = MagicMock
    qg.QCursor = MagicMock
    qg.QAction = MagicMock


_ensure_win32_mock()


# ── Fixtures ──

@pytest.fixture()
def tmp_config(tmp_path: Path):
    """Create a Config instance backed by a temporary file."""
    from src.core.config import Config
    config_path = tmp_path / "config.json"
    return Config(config_path=config_path)


@pytest.fixture()
def tmp_db(tmp_path: Path):
    """Create a volatile (in-memory) Database instance."""
    from src.core.database import Database
    from src.core.config import Config
    config = Config(config_path=tmp_path / "config.json")
    return Database(config=config)


@pytest.fixture()
def tmp_db_file(tmp_path: Path):
    """Create a file-backed Database instance."""
    from src.core.database import Database
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture()
def tmp_manager(tmp_path: Path, monkeypatch):
    """Create a ClipboardManager with a mocked listener."""
    from src.core.config import Config
    from src.core.database import Database
    from src.core.clipboard_manager import ClipboardManager

    config = Config(config_path=tmp_path / "config.json")
    db = Database(config=config)

    # Mock the listener so no Win32 message pump starts
    monkeypatch.setattr(
        "src.core.clipboard_manager.ClipboardListener",
        lambda callback: MagicMock(start=MagicMock(), stop=MagicMock()),
    )

    manager = ClipboardManager(db=db, config=config)
    return manager


@pytest.fixture()
def api_client(tmp_path: Path, monkeypatch):
    """Create a Starlette TestClient for the FastAPI app with fresh instances."""
    from starlette.testclient import TestClient
    from src.core.config import Config
    from src.core.database import Database
    from src.core.clipboard_manager import ClipboardManager
    import src.server as server_module

    config = Config(config_path=tmp_path / "config.json")
    db = Database(config=config)

    monkeypatch.setattr(
        "src.core.clipboard_manager.ClipboardListener",
        lambda callback: MagicMock(start=MagicMock(), stop=MagicMock()),
    )

    manager = ClipboardManager(db=db, config=config)

    # Replace the module-level globals used by all endpoints
    monkeypatch.setattr(server_module, "config", config)
    monkeypatch.setattr(server_module, "db", db)
    monkeypatch.setattr(server_module, "manager", manager)

    client = TestClient(server_module.app)
    yield client
    client.close()
