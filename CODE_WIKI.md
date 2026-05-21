# 拾遗 (ShiYi) - Code Wiki

## 1. 项目概述

### 1.1 项目简介
**拾遗 (ShiYi)** 是一款 Windows 桌面效率工具，定位为 **剪贴板管理器 + 文件中转站**。它帮助用户自动记录剪贴板历史、管理文件中转、通过标签系统组织内容，并提供强大的预览功能。

### 1.2 核心功能
- 📋 **剪贴板历史记录** - 自动捕获文本、图片、文件路径
- 📁 **文件中转站** - 拖拽文件到悬浮球，快速预览和分类
- 🏷️ **标签管理系统** - 为剪贴项和文件添加标签，方便检索
- 🔍 **全文搜索** - 快速搜索历史剪贴内容
- 📄 **多格式预览** - 支持文本、图片、Word、Excel、PDF、PPT 预览
- 📌 **固定常用项** - 固定重要内容不被自动清理
- 📤 **数据导出** - 支持导出为 TXT、CSV、JSON、Markdown 格式

### 1.3 技术栈
| 分类 | 技术 |
|------|------|
| **后端** | Python 3.11+, PyQt6, SQLite |
| **前端** | PyQt6 + QML |
| **图像处理** | Pillow |
| **文档预览** | python-docx, openpyxl, PyPDF2, python-pptx |
| **Web服务** | FastAPI, Uvicorn |

---

## 2. 项目架构

### 2.1 系统架构图
```
┌─────────────────────────────────────────────────────────┐
│                    PyQt6 + QML                           │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ TrayIcon     │  │  QmlBridge   │  │  GlobalHotkey │   │
│  └─────────────┘  └──────┬───────┘  └───────────────┘   │
│                          │ HTTP + WebSocket               │
│                          ↓                                │
│  ┌───────────────────────────────────────────────────┐   │
│  │              QML Main Panel                        │   │
│  │  TitleBar · FilterBar · TagBar · SearchBar         │   │
│  │  ClipboardListView · ActionBar · EmptyState        │   │
│  └───────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────┐   │
│  │  PreviewBar (悬浮球) · PreviewWindow               │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────┐
│                    Python 后端                            │
│  ┌─────────────┐  ┌──────┴───────┐  ┌───────────────┐   │
│  │   Config    │  │  FastAPI/WS  │  │   Database    │   │
│  └─────────────┘  │  :8199       │  │   (SQLite)    │   │
│                   └──────────────┘  └───────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │              ClipboardManager                     │   │
│  │  ┌──────────────────┐  ┌───────────────────────┐ │   │
│  │  │ClipboardListener │  │  Image Processing     │ │   │
│  │  │(Win32 message pump)│ │  (PIL compression)    │ │   │
│  │  └──────────────────┘  └───────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流
```
系统剪贴板变化
  → ClipboardListener (Win32 hidden HWND, WM_CLIPBOARDUPDATE)
    → ClipboardManager (去重、类型判断、入库)
      → Database (SQLite)
        → FastAPI WebSocket 推送
          → ApiClient 接收
            → QmlBridge + QClipboardListModel
              → QML 主面板更新
                → 用户点击条目 → HTTP 接口 → 写回系统剪贴板

悬浮球 ← PreviewBar ← api_client.items_changed 信号
托盘 ← TrayIcon ← api_client.status_changed 信号
```

### 2.3 线程模型
- **Python 主线程**: Uvicorn HTTP 服务器 + PyQt6 事件循环
- **Python 监听线程**: QThread 运行 Win32 消息泵，通过 Qt Signal 通知主线程

---

## 3. 目录结构

```
zhongzhuan/
├── .claude/                    # Claude AI 配置目录
│   └── agents/
├── docs/                        # 项目文档
│   ├── ARCHITECTURE.md         # 架构文档
│   └── PRD.md                  # 产品需求文档
├── scripts/                     # 辅助脚本
│   ├── generate_icons.py
│   └── setup-shell-integration.py
├── src/                         # Python 源代码
│   ├── core/                   # 核心功能模块
│   │   ├── __init__.py
│   │   ├── clipboard_listener.py   # Win32 剪贴板监听
│   │   ├── clipboard_manager.py    # 剪贴板管理器
│   │   ├── config.py              # 配置管理
│   │   └── database.py            # 数据库操作
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   └── clipboard_item.py     # 剪贴板项数据模型
│   ├── ui/                     # PyQt6 UI 组件
│   │   ├── previews/           # 文件预览器
│   │   │   ├── __init__.py
│   │   │   ├── excel_preview.py
│   │   │   ├── image_preview.py
│   │   │   ├── markdown_preview.py
│   │   │   ├── pdf_preview.py
│   │   │   ├── ppt_preview.py
│   │   │   └── text_preview.py
│   │   ├── __init__.py
│   │   ├── acrylic.py
│   │   ├── clipboard_item_delegate.py
│   │   ├── clipboard_item_widget.py
│   │   ├── clipboard_list_model.py
│   │   ├── drag_handler.py
│   │   ├── export_dialog.py
│   │   ├── export_progress_dialog.py
│   │   ├── floating_ball.py       # 悬浮球
│   │   ├── floating_panel.py      # 悬浮面板
│   │   ├── preview_bar.py         # 预览栏
│   │   ├── preview_window.py
│   │   ├── tag_chip.py
│   │   ├── tag_dialog.py
│   │   └── tray_icon.py           # 系统托盘图标
│   ├── utils/                  # 工具函数
│   │   ├── __init__.py
│   │   ├── autostart.py
│   │   ├── helpers.py
│   │   └── import_export.py       # 导入导出功能
│   ├── __init__.py
│   ├── api_client.py           # API 客户端
│   ├── app.py                  # PyQt6 应用入口
│   ├── main.py                 # 独立 PyQt6 入口
│   ├── run_server.py
│   └── server.py               # FastAPI 服务器
├── tests/                       # 测试文件
│   ├── __init__.py
│   ├── test_clipboard_item.py
│   ├── test_database.py
│   └── test_tags.py
├── .gitignore
├── CLAUDE.md
├── README.md
├── progress.md
└── requirements.txt             # Python 依赖
```

---

## 4. 核心模块说明

### 4.1 核心模块 ([src/core/](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/core))

#### 4.1.1 Config ([config.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/core/config.py))
配置管理模块，处理应用的配置信息。

**主要功能:**
- 存储模式管理：临时模式 (VOLATILE) vs 持久模式 (PERSISTENT)
- 最大条目数限制
- 图片大小限制和压缩质量配置
- 剪贴板监听开关
- 悬浮球位置保存

**关键枚举:**
```python
class StorageMode(str, Enum):
    VOLATILE = "volatile"      # 临时模式：重启清空
    PERSISTENT = "persistent"  # 持久模式：重启保留
```

#### 4.1.2 Database ([database.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/core/database.py))
SQLite 数据库封装，支持双模式存储。

**主要数据表:**
| 表名 | 说明 |
|------|------|
| `clipboard_items` | 剪贴板历史条目 |
| `tags` | 标签定义 |
| `item_tags` | 条目-标签关联表 |
| `groups` | 分组表 |
| `projects` | 项目表 |
| `clipboard_fts` | 全文搜索虚拟表 (FTS5) |

**核心方法:**
- `insert_item()`: 插入新条目
- `get_items()`: 获取条目列表
- `search()`: 全文搜索
- `exists_hash()`: 检查内容是否已存在 (去重用)
- `delete_oldest_non_pinned()`: 删除最旧的未固定条目

#### 4.1.3 ClipboardManager ([clipboard_manager.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/core/clipboard_manager.py))
中央剪贴板管理器，协调监听器、数据库和 UI 信号。

**核心功能:**
- 启动/停止剪贴板监听
- 处理剪贴板内容变更，去重
- 条目管理：添加、删除、固定、收藏
- 标签管理：创建、删除、应用标签
- 文件导入：支持拖拽文件导入
- 图片处理：压缩、缩略图生成

**关键方法:**
```python
def start(self) -> None:
    """启动剪贴板监听"""

def _on_clipboard_change(self) -> None:
    """剪贴板变化回调"""

def import_files(self, file_paths: list[str], ...) -> tuple[int, int]:
    """导入文件，返回 (导入数, 跳过数)"""

def copy_to_clipboard(self, item: ClipboardItem) -> None:
    """将条目复制回系统剪贴板"""

def search_with_filters(self, query, tag_ids, group_id, ...) -> list[ClipboardItem]:
    """组合搜索 + 标签 + 分组 + 分类过滤"""
```

#### 4.1.4 ClipboardListener ([clipboard_listener.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/core/clipboard_listener.py))
Win32 剪贴板监听器，使用隐藏窗口和 Windows 消息泵。

**功能:**
- 监听 `WM_CLIPBOARDUPDATE` 消息
- 读取不同格式的剪贴板内容：文本、图片、文件、HTML
- 写入剪贴板内容

### 4.2 数据模型 ([src/models/](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/models))

#### 4.2.1 ClipboardItem ([clipboard_item.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/models/clipboard_item.py))
剪贴板条目数据模型。

**内容类型枚举:**
```python
class ContentType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILES = "FILES"
    HTML = "HTML"
```

**分类枚举:**
```python
class Category(str, Enum):
    ALL = "ALL"
    DEFAULT = "DEFAULT"
    IMAGE = "IMAGE"
    WORD = "WORD"
    EXCEL = "EXCEL"
    PDF = "PDF"
    PPT = "PPT"
    ARCHIVE = "ARCHIVE"
```

**数据结构:**
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `content_type` | ContentType | 内容类型 |
| `content_text` | str | 文本内容 |
| `content_html` | str | HTML 内容 |
| `file_path` | str | 文件/图片路径 |
| `source_app` | str | 来源应用 |
| `is_pinned` | bool | 是否固定 |
| `is_favorite` | bool | 是否收藏 |
| `is_starred` | bool | 是否星标 |
| `group_id` | int | 分组 ID |
| `category` | str | 自动分类 |
| `tags` | list[Tag] | 标签列表 |
| `source` | str | 来源方式 |
| `project` | str | 项目 |
| `metadata` | str | 元数据 (JSON) |
| `content_hash` | str | SHA256 哈希 (去重用) |
| `created_at` | datetime | 创建时间 |

**关键方法:**
- `compute_hash()`: 计算内容的 SHA256 哈希
- `short_preview()`: 生成短文本预览
- `display_type`: 确定预览显示类型

### 4.3 UI 模块 ([src/ui/](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/ui))

#### 4.3.1 FloatingPanel ([floating_panel.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/ui/floating_panel.py))
主悬浮面板，提供剪贴板历史列表。

**主要功能:**
- 列表显示剪贴板历史
- 搜索功能
- 分类和标签筛选
- 项目筛选
- 多选和批量操作
- 条目预览
- 拖拽文件导入
- 键盘快捷键支持

**UI 组件:**
- 标题栏：状态指示、容量显示
- 筛选栏：项目选择、分类标签
- 搜索框：带防抖的搜索
- 列表视图：`QListView` + 自定义委托
- 多选操作栏

#### 4.3.2 PreviewBar ([preview_bar.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/ui/preview_bar.py))
悬浮球 + 变形预览栏。

**功能:**
- 悬浮球：拖拽文件、快捷入口
- 预览栏：临时预览区
- 展开/收起动画

#### 4.3.3 预览器 ([ui/previews/](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/ui/previews))
多种文件格式的预览组件。

| 文件类型 | 预览器 |
|----------|--------|
| 图片 | `image_preview.py` |
| Word | `word_preview.py` |
| Excel | `excel_preview.py` |
| PDF | `pdf_preview.py` |
| PPT | `ppt_preview.py` |
| Markdown | `markdown_preview.py` |
| 文本 | `text_preview.py` |

### 4.4 API 模块

#### 4.4.1 Server ([server.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/server.py))
FastAPI 服务器，提供 HTTP REST API 和 WebSocket 服务。

**运行参数:**
- Host: `127.0.0.1`
- Port: `8199`

**REST API 接口:**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 获取服务状态 |
| GET | `/api/items` | 分页获取条目列表 |
| GET | `/api/items/search` | 全文搜索 |
| POST | `/api/items/{item_id}/copy` | 复制条目到剪贴板 |
| DELETE | `/api/items/{item_id}` | 删除条目 |
| POST | `/api/items/{item_id}/pin` | 切换固定状态 |
| POST | `/api/items/{item_id}/favorite` | 切换收藏状态 |
| POST | `/api/items/{item_id}/star` | 切换星标状态 |
| POST | `/api/items/clear` | 清空所有条目 |
| POST | `/api/items/merge` | 合并条目 |
| POST | `/api/items/import` | 导入文件 |
| POST | `/api/items/import-text` | 导入文本 |
| GET | `/api/tags` | 获取所有标签 |
| POST | `/api/tags` | 创建标签 |
| PUT | `/api/tags/{tag_id}` | 更新标签 |
| DELETE | `/api/tags/{tag_id}` | 删除标签 |
| GET | `/api/items/{item_id}/tags` | 获取条目标签 |
| POST | `/api/items/{item_id}/tags` | 为条目添加标签 |
| DELETE | `/api/items/{item_id}/tags/{tag_id}` | 移除条目标签 |
| GET | `/api/groups` | 获取分组 |
| GET | `/api/projects` | 获取项目 |
| POST | `/api/projects` | 创建项目 |
| DELETE | `/api/projects/{project_id}` | 删除项目 |
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 更新配置 |

**WebSocket 接口:**
- `/ws`: 实时推送条目变更事件

#### 4.4.2 ApiClient ([api_client.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/api_client.py))
API 客户端，封装与服务器的通信。

**功能:**
- HTTP 请求封装
- WebSocket 连接管理
- 信号机制通知 UI 变更

### 4.5 应用入口

#### 4.5.1 main.py ([main.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/main.py))
独立 PyQt6 入口点。

**启动流程:**
1. 高 DPI 适配配置
2. 初始化 QApplication
3. 加载配置
4. 初始化 ClipboardManager
5. 创建 FloatingPanel
6. 创建 TrayIcon
7. 注册全局快捷键 (Ctrl+Shift+V)
8. 进入事件循环

#### 4.5.2 app.py ([app.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/app.py))
统一入口：FastAPI 服务器 + PyQt6 UI 在同一进程。

**启动流程:**
1. 配置异常处理和日志
2. 初始化共享实例 (Config, Database, ClipboardManager)
3. 启动 FastAPI 服务器 (后台线程)
4. 等待服务器就绪
5. 初始化 UI (FloatingPanel, PreviewBar, TrayIcon)
6. 连接信号
7. 进入事件循环

---

## 5. 关键类与函数详解

### 5.1 ClipboardManager 类

**位置:** [src/core/clipboard_manager.py:36](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/core/clipboard_manager.py#L36)

**核心成员变量:**
- `db`: Database 实例
- `config`: Config 实例
- `_listener`: ClipboardListener 实例
- `items_changed`: Qt 信号，通知 UI 刷新

**核心方法:**

#### `_on_clipboard_change()`
处理剪贴板变化：
1. 读取当前剪贴板内容
2. 计算哈希去重
3. 自动分类
4. 插入数据库
5. 容量管理（淘汰最旧条目）
6. 通知 UI

#### `_read_clipboard()` → `Optional[ClipboardItem]`
按优先级读取剪贴板内容：
1. 图片 (DIB 格式)
2. 文件路径
3. HTML
4. 纯文本

#### `_process_image(dib_data: bytes)` → `Optional[ClipboardItem]`
处理剪贴板图片：
1. 解析 DIB 格式为 BMP
2. 翻转图像 (DIB 是倒置的)
3. 压缩到配置的最大尺寸
4. 保存为 JPEG
5. 生成缩略图
6. 计算哈希

#### `import_files(file_paths, source, project, metadata)` → `tuple[int, int]`
导入文件：
1. 区分图片和普通文件
2. 图片：压缩、缩略图、哈希检查
3. 文本文件：读取内容
4. 普通文件：记录路径
5. 自动分类
6. 插入数据库
7. 容量管理

### 5.2 Database 类

**位置:** [src/core/database.py:17](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/core/database.py#L17)

**核心方法:**

#### `_conn()` → `Generator[sqlite3.Connection, None, None]`
上下文管理器，提供数据库连接：
- 内存模式：复用连接
- 持久模式：每次新建，启用 WAL

#### `init_db()`
初始化数据库表结构：
- 创建所有表
- 创建索引
- 初始化 FTS5 虚拟表
- 插入默认分组
- 列迁移（向后兼容）

#### `search_with_filters(query, tag_ids, group_id, category, project, limit)` → `list[ClipboardItem]`
组合过滤搜索：
- 文本搜索：FTS5 或 LIKE
- 标签过滤：多标签 AND
- 分组、分类、项目过滤
- 排序：固定项优先，然后按时间

#### `merge_items(item_ids, separator)` → `Optional[int]`
合并多个条目：
1. 获取待合并条目
2. 拼接文本和 HTML
3. 计算新哈希
4. 插入新条目
5. 返回新条目 ID

### 5.3 FloatingPanel 类

**位置:** [src/ui/floating_panel.py:77](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/ui/floating_panel.py#L77)

**核心方法:**

#### `refresh_list()`
刷新列表：
1. 清空模型
2. 应用所有过滤条件
3. 调用 API 获取条目
4. 更新模型
5. 更新空状态提示
6. 更新容量显示

#### `keyPressEvent(event)`
处理键盘快捷键：
- `Esc`: 清空搜索 / 关闭面板
- `Ctrl+V`: 粘贴收录
- `Ctrl+F`: 聚焦搜索框
- `Ctrl+A`: 全选 (多选模式)
- `Ctrl+E`: 导出
- `Ctrl+M`: 合并
- `Enter`: 复制条目
- `Shift+Enter`: 预览条目
- `Delete`: 删除条目
- `↑`/`↓`: 移动焦点

#### `_toggle_multi_select_from_btn(checked)`
切换多选模式：
- 显示/隐藏多选操作栏
- 更新委托状态
- 更新选择计数

### 5.4 FastAPI Server 关键函数

**位置:** [src/server.py](file:///g:/AI/app/zhongzhuan/zhongzhuan/src/server.py)

#### `lifespan(app)` → `AsyncContextManager`
应用生命周期管理：
- 启动：初始化管理器，启动监听
- 关闭：停止监听

#### `broadcast(event, data)` → `Awaitable[None]`
向所有连接的 WebSocket 客户端推送消息。

#### `on_items_changed()`
条目变化回调：
- 获取当前数量
- 通过 asyncio 调度广播

---

## 6. 依赖关系

### 6.1 Python 依赖 ([requirements.txt](file:///g:/AI/app/zhongzhuan/zhongzhuan/requirements.txt))

```
PyQt6>=6.6.0              # UI 框架
pywin32>=306              # Windows API 调用
Pillow>=10.0.0            # 图像处理
fastapi>=0.109.0          # Web 框架
uvicorn[standard]>=0.27.0 # ASGI 服务器
websockets>=12.0          # WebSocket 支持
websocket-client>=1.6.0   # WebSocket 客户端
pymupdf>=1.23.0           # PDF 处理
python-docx>=1.0.0        # Word 文档处理
python-pptx>=0.6.21       # PPT 处理
openpyxl>=3.1.0           # Excel 处理
markdown>=3.5.0           # Markdown 渲染
pygments>=2.17.0          # 代码高亮
```

### 6.2 模块依赖图

```
main.py/app.py
  ├── config.py
  ├── database.py
  │     └── config.py
  ├── clipboard_manager.py
  │     ├── config.py
  │     ├── database.py
  │     ├── clipboard_listener.py
  │     └── clipboard_item.py (models)
  ├── api_client.py
  │     └── server.py (HTTP)
  ├── server.py
  │     ├── config.py
  │     ├── database.py
  │     └── clipboard_manager.py
  └── ui/*.py
        ├── api_client.py
        ├── clipboard_item.py (models)
        └── ui/previews/*.py
```

---

## 7. 运行方式

### 7.1 开发模式运行

#### 方式一：纯 PyQt6 模式
```bash
python src/main.py
```

#### 方式二：统一模式 (推荐)
```bash
python src/app.py
```

#### 方式三：仅启动服务器
```bash
python src/server.py
```

### 7.2 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+V` | 打开/关闭面板 |
| `Esc` | 清空搜索 / 关闭面板 |
| `Ctrl+F` | 聚焦搜索框 |
| `Ctrl+A` | 全选 (多选模式) |
| `Ctrl+E` | 导出 |
| `Ctrl+M` | 合并条目 |
| `Enter` | 复制选中条目 |
| `Shift+Enter` | 预览选中条目 |
| `Delete` | 删除选中条目 |
| `↑`/`↓` | 移动列表焦点 |

### 7.3 配置文件

配置文件位置：`~/.eleven/config.json`

默认配置：
```json
{
  "storage_mode": "volatile",
  "max_items": 200,
  "max_image_size": [800, 800],
  "jpeg_quality": 85,
  "clipboard_enabled": false
}
```

### 7.4 数据存储

数据位置：`~/.eleven/`

- `data.db`: SQLite 数据库 (持久模式)
- `images/`: 图片存储目录
- `config.json`: 配置文件
- `server_error.log`: 服务器错误日志
- `eleven.log`: 应用日志

---

## 8. 开发指南

### 8.1 代码风格

- **类型注解**: 使用 Python 类型提示 (PEP 484)
- **格式化**: 遵循 PEP 8
- **Docstring**: 为公共类和函数编写文档字符串

### 8.2 添加新的预览器

1. 在 `src/ui/previews/` 创建新文件，如 `xyz_preview.py`
2. 实现预览组件类，继承自合适的基类
3. 在 `src/models/clipboard_item.py` 的 `display_type` 属性中添加对应类型
4. 在 `src/ui/preview_window.py` 中添加预览器实例化逻辑

### 8.3 添加新的 API 端点

1. 在 `src/server.py` 中添加新的 FastAPI 路由
2. 在 `src/api_client.py` 中添加对应方法
3. 如需要 WebSocket 推送，在 `broadcast()` 中添加事件

### 8.4 数据库迁移

在 `Database.init_db()` 中添加迁移代码，使用 `try-except` 确保向后兼容：

```python
try:
    conn.execute("ALTER TABLE table ADD COLUMN new_col TEXT")
except sqlite3.OperationalError:
    pass  # 列已存在，跳过
```

### 8.5 测试

运行测试：
```bash
python -m pytest tests/
```

测试文件位置：[tests/](file:///g:/AI/app/zhongzhuan/zhongzhuan/tests)

---

## 9. 常见问题与调试

### 9.1 日志查看

- 应用日志：`~/.eleven/eleven.log`
- 服务器错误：`~/.eleven/server_error.log`

### 9.2 常见问题

**Q: 剪贴板监听不工作？**
- 检查 `config.clipboard_enabled` 是否为 `True`
- 查看日志中是否有 Win32 API 错误

**Q: 图片预览模糊？**
- 调整 `config.max_image_size` 和 `config.jpeg_quality`

**Q: 数据丢失？**
- 检查是否在 `VOLATILE` 模式
- 确认 `data.db` 文件存在且可写

**Q: 端口 8199 被占用？**
- 检查是否有其他实例在运行
- 修改 `server.py` 中的端口配置

---

## 10. 版本历史

### v3.1.0 (2026-05-17)
- 初始版本发布
- 剪贴板监听和管理
- 文件中转站（拖拽上传）
- 标签系统
- 全文搜索
- 多格式文件预览
- 水墨风 UI 设计
- 悬浮球 + 列表面板
- 系统托盘集成
- 快捷键支持
- 导出功能 (TXT/CSV/JSON/Markdown)

---

## 附录

### A. 参考资源
- [README.md](file:///g:/AI/app/zhongzhuan/zhongzhuan/README.md) - 项目说明
- [ARCHITECTURE.md](file:///g:/AI/app/zhongzhuan/zhongzhuan/docs/ARCHITECTURE.md) - 架构文档
- [PyQt6 文档](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

### B. 联系方式
- GitHub Issues: https://github.com/Moon-k-ctrl/eleven/issues
- Email: 545591243zx@gmail.com

---

**文档版本**: 1.0  
**最后更新**: 2026-05-17
