# 拾遗 (ShiYi) - Windows 桌面中转站

<div align="center">

**Windows 桌面效率工具 - 剪贴板管理器 + 文件中转站**

[![GitHub release](https://img.shields.io/badge/release-v3.1.0-blue)](https://github.com/Moon-k-ctrl/eleven)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.11-green?logo=qt)](https://www.riverbankcomputing.com/software/pyqt/)

</div>

---

## 📦 项目简介

**拾遗** 是一款 Windows 桌面效率工具，定位为 **剪贴板管理器 + 文件中转站**。

核心功能：
- 📋 **剪贴板历史**：自动记录剪贴板内容，随时回溯
- 📁 **文件中转**：拖拽文件到悬浮球，快速预览和分类
- 🏷️ **标签管理**：为剪贴项和文件添加标签，方便检索
- 🔍 **快速搜索**：支持全文搜索，快速定位历史内容
- 🎨 **水墨风 UI**：东方美学设计，墨分五色配色体系

---

## ✨ 功能特性

### 核心功能
| 功能 | 说明 |
|------|------|
| 📋 剪贴板监听 | 自动捕获文本、图片、文件路径 |
| 📁 文件中转站 | 拖拽文件到悬浮球，暂存并分类 |
| 🏷️ 标签系统 | 为每条记录添加多标签，支持筛选 |
| 🔍 全文搜索 | 快速搜索历史剪贴内容 |
| 📌 固定重要项 | 固定常用剪贴，不被自动清理 |
| 📤 导出功能 | 导出为 TXT / CSV / JSON / Markdown |

### 预览支持
- 📄 **文本**：纯文本预览
- 🖼️ **图片**：JPG/PNG/GIF/WEBP 预览
- 📝 **Word**：DOCX 文档预览
- 📊 **Excel**：XLSX 表格预览
- 📋 **PDF**：PDF 文档预览
- 📽️ **PPT**：PPTX 演示文稿预览

---

## 🎨 UI 设计

**水墨风设计语言**：
- 配色：墨分五色（焦、浓、重、淡、清）
- 布局：标题栏 + 筛选区 + 标签行 + 列表面板
- 动画：悬浮球扩散/收拢，流畅自然

> UI 设计详情请查看 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## 🛠️ 技术栈

### 后端
- **Python 3.11+**
- **PyQt6**：UI 框架
- **SQLite**：本地数据库
- **Pillow**：图片处理
- **python-docx / openpyxl / PyPDF2 / python-pptx**：文件预览

### 前端
- **QML**：声明式 UI，与 PyQt6 深度集成
- **PyQt6 QML Engine**：渲染引擎

---

## 📥 安装

### 方式一：下载发布版（推荐）
1. 前往 [Releases](https://github.com/Moon-k-ctrl/eleven/releases) 页面
2. 下载最新版 `eleven-setup-v3.1.0.exe`
3. 双击安装，按向导完成

### 方式二：从源码构建
```bash
# 克隆仓库
git clone https://github.com/Moon-k-ctrl/eleven.git
cd eleven

# 安装 Python 依赖
pip install -r requirements.txt

# 运行（开发模式）
python -m src.app

# 打包（PyInstaller）
pyinstaller eleven.spec --noconfirm
```

---

## 🚀 使用方法

### 基本操作
1. **启动**：运行 `eleven.exe` 或从源码运行 `python src/main.py`
2. **剪贴板监听**：自动在后台运行，记录剪贴内容
3. **打开面板**：点击系统托盘图标 或 按快捷键 `Win+Shift+V`
4. **文件中转**：拖拽文件到悬浮球，自动添加到中转站
5. **搜索**：在搜索框输入关键词，实时过滤
6. **标签筛选**：点击标签 chip，快速筛选

### 快捷键
| 快捷键 | 功能 |
|--------|------|
| `Win+Shift+V` | 打开/隐藏 列表面板 |
| `Esc` | 隐藏面板 |
| `Ctrl+F` | 聚焦搜索框 |
| `Delete` | 删除选中项 |

---

## 📂 项目结构

```
eleven/
├── src/                  # Python 后端源码
│   ├── core/            # 核心功能（剪贴板监听、管理器、配置、数据库）
│   ├── models/          # 数据模型
│   ├── ui/              # PyQt6/QML UI（面板、悬浮球、托盘、预览）
│   │   ├── qml/        # QML 主面板、组件、主题
│   │   └── previews/   # 文件预览器（图片、Word、Excel、PDF、PPT）
│   ├── utils/           # 工具函数（自启动、导入导出）
│   ├── main.py          # 后端入口
│   ├── app.py           # PyQt6 应用
│   └── server.py       # 本地 HTTP 服务器
├── docs/                # 文档
│   ├── ARCHITECTURE.md  # 架构说明
│   └── PRD.md          # 产品需求文档
├── scripts/              # 辅助脚本
├── tests/               # 单元测试
├── requirements.txt      # Python 依赖
├── eleven.spec          # PyInstaller 配置
└── README.md            # 本文件
```

---

## 🔧 开发

### 运行开发模式
```bash
python -m src.app
```

### 构建发布版
```bash
pyinstaller eleven.spec --noconfirm
```

---

## 📝 更新日志

### v3.1.0 (2026-05-17)
- ✅ 初始版本发布
- ✅ 剪贴板监听和管理
- ✅ 文件中转站（拖拽上传）
- ✅ 标签系统
- ✅ 全文搜索
- ✅ 多格式文件预览（文本/图片/Word/Excel/PDF/PPT）
- ✅ 水墨风 UI 设计
- ✅ 悬浮球 + 列表面板
- ✅ 系统托盘集成
- ✅ 快捷键支持
- ✅ 导出功能（TXT/CSV/JSON/Markdown）

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [Python](https://www.python.org/)
- [Pillow](https://python-pillow.org/)
- [python-docx](https://python-docx.readthedocs.io/)
- [openpyxl](https://openpyxl.readthedocs.io/)
- [PyPDF2](https://pypdf2.readthedocs.io/)
- [python-pptx](https://python-pptx.readthedocs.io/)

---

## 📧 联系

- GitHub Issues：[https://github.com/Moon-k-ctrl/eleven/issues](https://github.com/Moon-k-ctrl/eleven/issues)
- Email：545591243zx@gmail.com

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！⭐**

</div>
