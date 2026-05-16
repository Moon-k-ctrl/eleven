# 架构文档

## 技术栈
- **后端**: Python 3.12 + pywin32 (Win32 API) + Pillow (图片处理) + FastAPI + uvicorn
- **前端**: Electron 28+ + HTML/CSS/JS
- **数据库**: SQLite (本地持久化，FTS5 全文搜索)
- **通信**: HTTP REST API + WebSocket 实时推送

## 系统架构
```
┌─────────────────────────────────────────────────────────┐
│                    Electron 主进程                        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ TrayManager  │  │GatewayMonitor│  │ShortcutManager│   │
│  └─────────────┘  └──────┬───────┘  └───────────────┘   │
│                          │ HTTP + WebSocket               │
│  ┌───────────────────────┴───────────────────────────┐   │
│  │              child_process.spawn                   │   │
│  └───────────────────────┬───────────────────────────┘   │
└──────────────────────────┼──────────────────────────────┘
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
          → Electron GatewayMonitor 接收
            → IPC 通知渲染进程
              → 悬浮条/ Dashboard UI 更新
                → 用户点击条目 → HTTP API → 写回系统剪贴板
```

## 线程模型
- **Python 主线程**: uvicorn HTTP 服务器
- **Python 监听线程**: QThread 运行 Win32 消息泵，通过 Qt Signal 通知主线程
- **Electron 主进程**: Node.js 事件循环 + IPC
- **Electron 渲染进程**: Chromium 渲染 UI

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
| POST | `/api/items/clear` | 清空所有条目 |
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 更新配置 |

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
    group_id    INTEGER,
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
│   ├── main.py                   # 独立 PyQt6 入口（备用）
│   ├── core/
│   │   ├── clipboard_listener.py # Win32 剪贴板监听
│   │   ├── clipboard_manager.py  # 核心管理器
│   │   ├── config.py             # 双存储模式配置
│   │   └── database.py           # SQLite 封装
│   ├── models/
│   │   └── clipboard_item.py     # 数据模型
│   ├── ui/                       # PyQt6 UI（独立模式备用）
│   └── utils/
├── electron/                     # Electron 前端
│   ├── package.json
│   ├── main.js                   # 主进程入口 + Python 子进程管理
│   ├── preload.js                # IPC 桥接
│   ├── index.html                # 悬浮条 + 下拉列表
│   ├── dashboard.html            # 详情面板
│   ├── styles.css                # 样式
│   ├── main/
│   │   ├── tray.js               # 系统托盘
│   │   ├── gateway-monitor.js    # HTTP + WebSocket 数据采集
│   │   ├── dashboard-window.js   # 详情面板窗口
│   │   └── shortcuts.js          # 全局快捷键
│   └── renderer/
│       ├── drag-position.js      # 拖拽移动
│       ├── state-machine.js      # 状态机
│       ├── renderer.js           # 数据绑定 + 列表渲染
│       └── notification.js       # 气泡通知
├── tests/
└── docs/
```

## 启动流程
```
npm start (electron/)
  → child_process.spawn('python', ['-m', 'src.server'])
    → Python 初始化 Config + Database + ClipboardManager
    → uvicorn 启动 HTTP/WS 服务 (端口 8199)
  → Electron 等待 /api/status 就绪
  → 创建悬浮窗口
  → GatewayMonitor 连接 HTTP + WebSocket
  → 渲染进程显示实时数据
```

## 关键设计决策
1. **Electron 作为 UI**: 跨平台潜力，Web 技术栈开发效率高，透明悬浮窗支持好
2. **Python 作为后端**: pywin32 直接访问 Win32 API，PIL 图片处理成熟
3. **HTTP + WebSocket**: REST 用于 CRUD 操作，WebSocket 用于实时推送
4. **子进程架构**: Electron 通过 child_process.spawn 管理 Python 进程生命周期
5. **SQLite + FTS5**: 零依赖，单文件，全文搜索
6. **SHA256 去重**: content_hash 避免重复存储相同内容
7. **双存储模式**: volatile (内存) / persistent (磁盘) 可切换
