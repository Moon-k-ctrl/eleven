# 拾遗 (eleven)

Windows 桌面剪贴板管理工具。支持多内容暂存、图片/文件/文字混合存储、全局快捷键浮窗面板。

## Tech Stack
- Python 3.11 + PyQt6 + pywin32 + Pillow
- SQLite (本地存储)
- Windows-only (Win10/11)

## Run
```bash
pip install -r requirements.txt
python -m src.main
```

## Server Mode (with Electron UI)
```bash
python -m src.server
```

## Test
```bash
pytest tests/
```

## Build
```bash
pyinstaller eleven-backend.spec
```

## Structure
```
src/
  core/           # 剪贴板监听、管理器、数据库
  ui/             # PyQt6 浮窗面板、条目组件
  models/         # 数据模型
  utils/          # 工具函数
electron/         # Electron 前端
tests/            # 测试
docs/             # PRD、架构文档
```

## Conventions
- 中文注释可以，docstring 用英文
- 必须加 type hints
- 当前阶段：MVP（仅 P0 功能）
- 核心数据流：系统剪贴板 → Listener → Manager → Database → UI
