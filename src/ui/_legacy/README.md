# Legacy PyQt6 UI Files

These files are the original PyQt6 widget-based UI, replaced by the QML-based UI (`src/ui/qml/`).

## Files

| File | Replaced By |
|------|-------------|
| `main.py` | `src/app.py` (QML entry point) |
| `floating_panel.py` | `src/ui/qml/main.qml` |
| `clipboard_item_delegate.py` | `src/ui/qml/components/ClipboardItemDelegate.qml` |
| `clipboard_item_widget.py` | `src/ui/qml/components/ClipboardItemDelegate.qml` |
| `clipboard_list_model.py` | `src/ui/qml/bridge/clipboard_model.py` (QClipboardListModel) |
| `tag_chip.py` | `src/ui/qml/components/TagChip.qml` |

## Still Active

These files remain in `src/ui/` because they are still used:

- `drag_handler.py` — used by `preview_bar.py`
- `preview_bar.py` — floating ball + preview bar (QPainter-based, not QML)
- `floating_ball.py` — floating ball animation
- `tray_icon.py` — system tray
- `preview_window.py` — preview popup window
- `export_dialog.py` — export dialog (used by tray menu)
