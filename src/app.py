"""Unified entry point: FastAPI server + PyQt6 UI in one process."""
from __future__ import annotations

import os
import sys

# PyInstaller console=False 时 sys.stdout/stderr 为 None，uvicorn 会崩溃
if getattr(sys, 'frozen', False) and sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if getattr(sys, 'frozen', False) and sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

import logging
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from src.api_client import ApiClient
from src.core.clipboard_manager import ClipboardManager
from src.core.config import Config, StorageMode
from src.core.database import Database
from src.ui.preview_bar import PreviewBar
from src.ui.floating_panel import FloatingPanel
from src.ui.tray_icon import TrayIcon
from src.utils.import_export import (
    export_to_csv,
    export_to_json,
    import_from_csv,
    import_from_json,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eleven")

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8199
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"


def _start_server_thread(config: Config, db: Database,
                         manager: ClipboardManager) -> threading.Thread:
    """Start uvicorn in a daemon thread, sharing process-level instances."""
    import src.server as server_module

    # Patch server module globals so the FastAPI app uses our instances
    server_module.config = config
    server_module.db = db
    server_module.manager = manager

    import uvicorn

    def _run() -> None:
        log_path = Path.home() / ".eleven" / "server_error.log"
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("Server thread starting...\n")
                f.write(f"frozen={getattr(sys, 'frozen', False)}\n")
                f.write(f"executable={sys.executable}\n")
            uvicorn_config = uvicorn.Config(
                server_module.app,
                host=SERVER_HOST,
                port=SERVER_PORT,
                log_level="warning",
            )
            srv = uvicorn.Server(uvicorn_config)
            srv.run()
        except Exception:
            import traceback
            with open(log_path, "a", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            logger.error("Server thread crashed", exc_info=True)

    t = threading.Thread(target=_run, daemon=True, name="fastapi-server")
    t.start()
    return t


def _wait_for_server(timeout: float = 15.0) -> bool:
    """Poll /api/status until the server is ready."""
    deadline = time.monotonic() + timeout
    url = f"{BASE_URL}/api/status"
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.3)
    return False


def main() -> None:
    # 全局异常处理 — 防止未捕获异常导致静默崩溃
    log_dir = Path.home() / ".eleven"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "eleven.log"

    # 配置根日志 —— 显式添加 handler，因为 uvicorn 可能已抢先调用 basicConfig
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(fmt)
    root_logger.addHandler(fh)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
               for h in root_logger.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root_logger.addHandler(sh)

    def _handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _handle_exception

    # High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Shared instances
    config = Config()
    db = Database(config=config)
    manager = ClipboardManager(db=db, config=config)

    # Start FastAPI server in background thread
    logger.info("Starting internal server...")
    _start_server_thread(config, db, manager)

    # Wait for server to be ready
    if not _wait_for_server():
        # 读取错误日志获取详细信息
        error_log = Path.home() / ".eleven" / "server_error.log"
        detail = ""
        if error_log.exists():
            detail = f"\n\n详细错误:\n{error_log.read_text(encoding='utf-8').strip()}"
        QMessageBox.critical(
            None, "启动失败",
            f"内部服务启动超时，请重试。\n\n"
            f"如果问题持续，请检查是否有其他实例正在运行。{detail}"
        )
        sys.exit(1)
    logger.info("Server is ready")

    # Clipboard monitoring is started by the server lifespan

    # Create API client (talks to the internal server)
    api_client = ApiClient(base_url=BASE_URL)
    api_client.start()

    # UI
    panel = FloatingPanel(api_client)

    # v4.0 预览栏（悬浮球 + 变形预览）
    preview_bar = PreviewBar()
    preview_bar.clicked.connect(panel.toggle)
    preview_bar.expand_requested.connect(lambda: (panel.show(), panel.raise_()))
    preview_bar.files_dropped.connect(
        lambda paths: (api_client.import_files(paths, "drag-drop"), panel.refresh_list())
    )
    api_client.items_changed.connect(lambda: preview_bar.update_badge(api_client.get_count()))
    # 列表面板「发送到预览栏」
    panel.send_to_preview.connect(lambda items: (preview_bar.add_items(items), panel.hide()))
    panel.preview_bar_toggle.connect(preview_bar.toggle)
    # 悬浮球右键菜单信号
    preview_bar.panel_show_requested.connect(lambda: (panel.show(), panel.raise_(), panel.search_box.setFocus()))
    preview_bar.hide_ball_requested.connect(preview_bar.hide)
    preview_bar.quit_requested.connect(app.quit)
    preview_bar.toggle_monitoring_requested.connect(
        lambda: (setattr(config, 'clipboard_enabled', not config.clipboard_enabled),
                 tray.showMessage("拾遗", f"剪贴板监听已{'开启' if config.clipboard_enabled else '关闭'}"))
    )
    preview_bar.copy_item_requested.connect(api_client.copy_item)
    preview_bar.preview_item_requested.connect(panel._on_preview_requested)
    preview_bar.remove_item_requested.connect(lambda item_id: None)  # 仅从预览栏移除
    preview_bar.show()

    # Tray icon
    tray = TrayIcon(config=config)
    tray.toggle_panel.connect(panel.toggle)
    tray.toggle_ball.connect(preview_bar.toggle)
    tray.quit_app.connect(app.quit)

    # Status state machine: ApiClient status → tray icon + preview bar
    def _on_status_changed(status: str):
        tray.update_status(status)
        preview_bar.update_status(status)
        panel.update_status(status)
        if status == "online":
            tooltip = "拾遗 - 在线 | Ctrl+Shift+V 唤出"
        elif status == "warning":
            tooltip = "拾遗 - 警告 | Ctrl+Shift+V 唤出"
        elif status == "error":
            tooltip = "拾遗 - 错误 | Ctrl+Shift+V 唤出"
        else:
            tooltip = "拾遗 - 离线 | Ctrl+Shift+V 唤出"
        tray.setToolTip(tooltip)

    api_client.status_changed.connect(_on_status_changed)

    def on_storage_mode_changed(mode: StorageMode):
        QMessageBox.information(
            None,
            "存储模式已切换",
            f"已切换到{'临时' if mode == StorageMode.VOLATILE else '持久'}模式。\n\n请重启程序使更改生效。",
        )

    tray.storage_mode_changed.connect(on_storage_mode_changed)

    # Import/export (direct DB access — same process)
    def do_export_json():
        path, _ = QFileDialog.getSaveFileName(
            None, "导出 JSON", "clipboard_export.json",
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            count = export_to_json(db, Path(path))
            tray.showMessage("拾遗", f"已导出 {count} 条记录")

    def do_import_json():
        path, _ = QFileDialog.getOpenFileName(
            None, "导入 JSON", "",
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            count = import_from_json(db, Path(path))
            api_client.items_changed.emit()
            tray.showMessage("拾遗", f"已导入 {count} 条记录")

    def do_export_csv():
        path, _ = QFileDialog.getSaveFileName(
            None, "导出 CSV", "clipboard_export.csv",
            "CSV 文件 (*.csv);;所有文件 (*)"
        )
        if path:
            count = export_to_csv(db, Path(path))
            tray.showMessage("拾遗", f"已导出 {count} 条记录")

    def do_import_csv():
        path, _ = QFileDialog.getOpenFileName(
            None, "导入 CSV", "",
            "CSV 文件 (*.csv);;所有文件 (*)"
        )
        if path:
            count = import_from_csv(db, Path(path))
            api_client.items_changed.emit()
            tray.showMessage("拾遗", f"已导入 {count} 条记录")

    tray.export_json.connect(do_export_json)
    tray.import_json.connect(do_import_json)
    tray.export_csv.connect(do_export_csv)
    tray.import_csv.connect(do_import_csv)

    tray.show()

    # Global shortcut Ctrl+Shift+V
    shortcut = QShortcut(QKeySequence("Ctrl+Shift+V"), panel)
    shortcut.activated.connect(panel.toggle)

    # Global shortcut Ctrl+Shift+C — 截取选区内容
    def _capture_selection():
        """Save clipboard → simulate Ctrl+C → read new clipboard → import → restore."""
        import subprocess
        from PyQt6.QtGui import QGuiApplication

        clipboard = QGuiApplication.clipboard()
        # 1. Save original clipboard
        orig_mime = clipboard.mimeData()
        orig_text = orig_mime.text() if orig_mime else ""
        orig_html = orig_mime.html() if orig_mime else ""
        orig_has_image = clipboard.mimeData().hasImage() if clipboard.mimeData() else False

        # 2. Simulate Ctrl+C via PowerShell
        try:
            subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms;"
                 " [System.Windows.Forms.SendKeys]::SendWait('^c')"],
                timeout=3, capture_output=True,
            )
        except Exception:
            logger.warning("Failed to simulate Ctrl+C")
            return

        # 3. Wait for clipboard update
        import time
        time.sleep(0.3)

        # 4. Read new clipboard content
        new_mime = clipboard.mimeData()
        new_text = new_mime.text() if new_mime else ""
        new_html = new_mime.html() if new_mime else ""

        # 5. Check if content changed
        if new_text and new_text != orig_text:
            try:
                api_client.import_text(new_text, new_html, source="hotkey")
                tray.showMessage("拾遗", f"已截取选区内容 ({len(new_text)} 字符)")
            except Exception:
                logger.error("Failed to import captured text", exc_info=True)
        elif new_html and new_html != orig_html:
            try:
                api_client.import_text(new_text, new_html, source="hotkey")
                tray.showMessage("拾遗", "已截取选区 HTML 内容")
            except Exception:
                logger.error("Failed to import captured HTML", exc_info=True)
        else:
            logger.info("Capture: clipboard content unchanged")

        # 6. Restore original clipboard
        try:
            restore_mime = QMimeData()
            if orig_html:
                restore_mime.setHtml(orig_html)
            if orig_text:
                restore_mime.setText(orig_text)
            clipboard.setMimeData(restore_mime)
        except Exception:
            logger.warning("Failed to restore original clipboard")

    capture_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), panel)
    capture_shortcut.activated.connect(_capture_selection)

    logger.info("Running. Ctrl+Shift+V: toggle panel, Ctrl+Shift+C: capture selection.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
