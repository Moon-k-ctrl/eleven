# 架构文档

## 技术栈
- **后端**: Python 3.12 + pywin32 (Win32 API) + Pillow (图片处理) + FastAPI + uvicorn
- **前端**: PyQt6 + QML（桌面 UI）
- **数据库**: SQLite (本地持久化，FTS5 全文搜索)
- **通信**: HTTP REST API + WebSocket 实时推送

## 系统架构
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
┌──────────────────────────┼──────────────────────────────┐
│                    Python 后端                            │
│  ┌─────────────┐  ┌──────┴───────┐  ┌───────────────┐   │
│  │Config       │  │ FastAPI/WS   │  │  Database      │   │
│  └─────────────┘  │ :8199        │  │  (SQLite)      │   │
│                   └──────────────┘  └───────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │          ClipboardManager                         │   │
│  │  ┌──────────────────┐  ┌───────────────────────┐ │   │
│  │  │ClipboardListener  │  │ Image Processing      │ │   │
│  │  │(Win32 message pump)│  │ (PIL compression)    │ │   │
│  │  └──────────────────┘  └───────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 核心数据流
```
系统剪贴板变化
  → ClipboardListener (Win32 hidden HWND, WM_CLIPBOARDUPDATE)
    → ClipboardManager (去重、类型判断、入库)
      → Database (SQLite)
        → FastAPI WebSocket 推送
          → ApiClient 接收
            → QmlBridge + QClipboardListModel
              → QML 主面板更新
                → 用户点击条目 → HTTP API → 写回系统剪贴板

悬浮球 ← PreviewBar ← api_client.items_changed 信号
托盘 ← TrayIcon ← api_client.status_changed 信号
```

## 线程模型
- **Python 主线程**: uvicorn HTTP 服务器 + PyQt6 事件循环
- **Python 监听线程**: QThread 运行 Win32 消息泵，通过 Qt Signal 通知主线程

## API 接口

### REST API (http://127.0.0.1:8199)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 获取状态 `{status, count, max_items, storage_mode}` |
| GET | `/api/items?limit=50&cursor=` | 分页获取剪贴板列表 |
| GET | `/api/items/search?q=` | FTS5 全文搜索 |
| POST | `/api/items/{id}/copy` | 复制条目到系统剪贴板 |
| DELETE | `/api/items/{id}` | 删除条目 |
| POST | `/api/items/{id}/pin` | 切换置顶状态 |
| POST | `/api/items/{id}/favorite` | 切换收藏 |
| POST | `/api/items/{id}/star` | 切换星标 |
| POST | `/api/items/batch-delete` | 批量删除 |
| POST | `/api/items/merge` | 合并多条 |
| POST | `/api/items/clear` | 清空所有条目 |
| POST | `/api/items/import` | 导入文件 |
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 更新配置 |
| GET/POST | `/api/tags` | 标签 CRUD |
| POST/DELETE | `/api/items/{id}/tags` | 条目标签关联 |

### WebSocket (ws://127.0.0.1:8199/ws)

```json
// 服务端推送
{"event": "items-changed", "data": {"count": 42}}

// 客户端心跳
{"action": "ping"} → {"event": "pong"}
```

## 数据库 Schema
```sql
CREATE TABLE clipboard_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,      -- TEXT, IMAGE, FILES, HTML
    content_text TEXT,               -- 纯文本内容
    content_html TEXT,               -- HTML/RTF 源码
    file_path   TEXT,                -- 图片存储路径
    source_app  TEXT,                -- 来源窗口标题
    is_pinned   BOOLEAN DEFAULT 0,
    is_favorite BOOLEAN DEFAULT 0,
    is_starred  BOOLEAN DEFAULT 0,
    category    TEXT DEFAULT 'DEFAULT',
    display_type TEXT DEFAULT 'text',
    thumbnail_path TEXT,             -- 缩略图路径
    content_hash TEXT,               -- SHA256 去重
    sort_order  INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE clipboard_fts USING fts5(content_text);
```

## 目录结构
```
zhongzhuan/
├── requirements.txt              # Python 依赖
├── src/                          # Python 后端
│   ├── server.py                 # FastAPI + WebSocket 服务
│   ├── app.py                    # PyQt6 + QML 应用入口
│   ├── core/
│   │   ├── clipboard_listener.py # Win32 剪贴板监听
│   │   ├── clipboard_manager.py  # 核心管理器
│   │   ├── config.py             # 双存储模式配置
│   │   └── database.py           # SQLite 封装
│   ├── models/
│   │   └── clipboard_item.py     # 数据模型
│   ├── ui/
│   │   ├── qml/                  # QML 主面板、组件、主题
│   │   ├── floating_ball.py      # 悬浮球
│   │   ├── preview_bar.py        # 预览栏
│   │   ├── tray_icon.py          # 系统托盘
│   │   └── previews/             # 文件预览器
│   └── utils/
├── tests/
├── docs/
└── scripts/
```

## 启动流程
```
python -m src.app
  → PyQt6 QApplication 初始化
  → FastAPI server 启动 (端口 8199)
  → ApiClient 连接 HTTP + WebSocket
  → QmlBridge 注册到 QML 上下文
  → QML 主面板加载
  → TrayIcon 创建系统托盘
  → GlobalHotkey 注册 Ctrl+Shift+V / Ctrl+Shift+C
  → ClipboardListener 开始监听
```

## 关键设计决策
1. **PyQt6 + QML 作为 UI**: 原生性能，QML 声明式布局，深度集成 Python
2. **Python 作为后端**: pywin32 直接访问 Win32 API，PIL 图片处理成熟
3. **HTTP + WebSocket**: REST 用于 CRUD 操作，WebSocket 用于实时推送
4. **SQLite + FTS5**: 零依赖，单文件，全文搜索
5. **SHA256 去重**: content_hash 避免重复存储相同内容
6. **双存储模式**: volatile (内存) / persistent (磁盘) 可切换
