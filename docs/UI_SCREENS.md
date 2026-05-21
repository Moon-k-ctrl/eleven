# 拾遗 UI 界面与功能一览

> 最后更新：2026-05-18

---

## 1. 主面板（QML Panel）

**入口**：`src/app.py` → `src/ui/qml/main.qml`  
**唤出方式**：`Ctrl+Shift+V` 全局热键 / 系统托盘菜单 / 悬浮球点击  
**窗口规格**：430×520px，无边框，置顶，暗色背景 `#0C1116`

### 1.1 标题栏 — `TitleBar.qml`

| 区域 | 内容 | 交互 |
|------|------|------|
| 第一行 | 状态点（绿/黄/红/灰）+ "拾遗" + 容量 "(N/200)" + 最小化 + 关闭 | 拖拽标题文字移动窗口；最小化/关闭按钮 |
| 第二行 | 4 列按钮网格：合并、预览栏、导出、清空 | 合并仅多选时可见；清空为危险样式 |

### 1.2 分类筛选栏 — `FilterBar.qml` + `CategoryButton.qml`

8 个分类按钮：全部 / 文本 / 图片 / Word / Excel / PDF / PPT / 压缩  
点击切换筛选，激活态为薄荷绿背景。

### 1.3 标签栏 — `TagBar.qml` + `TagChip.qml`

水平滚动标签列表，从后端动态加载。  
点击标签切换筛选；`+` 按钮预留标签管理入口。

### 1.4 搜索框 — `SearchBar.qml`

- 输入即搜（300ms 防抖）
- `Enter` 立即搜索，`Escape` 清空
- 聚焦时薄荷绿边框

### 1.5 多选操作栏 — `ActionBar.qml`

仅多选模式下显示。包含：已选计数、全选、导出、删除（红色）、取消。

### 1.6 剪贴板列表 — `ClipboardListView.qml` + `ClipboardItemDelegate.qml`

每条记录 72px 高，从左到右：

| 区域 | 说明 |
|------|------|
| 复选框 | 多选模式下显示，薄荷绿 |
| 类型图标 / 缩略图 | 48×48；图片显示缩略图；文件按类型着色（W=蓝/E=绿/P=红/T=黄/A=紫） |
| 主标题 | 文件名或内容摘要，加粗 |
| 副标题 | 文件夹名/文件数量 + 时间 + 来源图标 + 标签 |
| 状态图标 | 置顶/收藏/星标 |

**交互**：
- 左键 → 复制到剪贴板（多选时切换选中）
- 右键 → 上下文菜单（复制/预览/收藏/星标/置顶/删除/多选模式）
- 双键 → 打开预览窗口

### 1.7 空状态 — `EmptyState.qml`

- 无内容："暂无剪贴内容" + "复制内容后将自动出现在这里"
- 搜索无结果："未找到匹配内容"

### 1.8 拖拽导入 — `DropOverlay.qml`

拖拽文件到面板时显示薄荷绿虚线边框覆盖层，释放后导入文件。

### 1.9 面板内快捷键

| 快捷键 | 功能 |
|--------|------|
| `Escape` | 清空搜索 / 隐藏面板 |
| `Ctrl+V` | 从系统剪贴板粘贴导入 |
| `Ctrl+F` | 聚焦搜索框 |
| `Ctrl+A` | 全选（仅多选模式） |

---

## 2. 悬浮球与预览栏 — `PreviewBar.py`

**入口**：`src/app.py` → `src/ui/preview_bar.py`  
**规格**：常驻桌面的浮动组件，两种形态

### 2.1 悬浮球模式

- 80px 圆形渐变（暖金色），中心 📦 图标
- 右上角红色数字角标（最多 99+）
- 左下角状态点（绿/黄/红/灰）
- 拖拽文件到球上：脉冲虚线动画 + 导入闪光

### 2.2 预览栏模式

- 320px 宽纵向列表，350ms 形变动画展开
- 每行 64px：缩略图 + 文件名 + 类型/大小
- 右侧操作区：展开按钮 ▲ / 计数 / 关闭 ✕
- 鼠标滚轮滚动

### 2.3 交互

| 操作 | 效果 |
|------|------|
| 左键单击球 | 有内容时形变为预览栏 |
| 双击球 | 打开主面板 |
| 右键球 | 菜单：显示面板 / 隐藏悬浮球 / 暂停监听 / 退出 |
| 拖拽球 | 移动位置（边缘吸附） |
| 悬停 600ms | 自动展开预览栏 |
| 右键缩略图 | 菜单：复制 / 预览 / 用默认程序打开 / 从预览栏移除 |
| 拖拽缩略图 | 将内容拖出到其他应用 |
| 拖入文件 | 导入到收藏 |

---

## 3. 预览窗口 — `PreviewWindow.py`

**入口**：双击列表项 / 预览栏右键菜单  
**规格**：屏幕 70%×80%，深色背景 `#121212`

### 3.1 支持的预览类型

| 类型 | 渲染器 | 特性 |
|------|--------|------|
| 文本 / HTML | `TextPreview` | 自动换行，A-/A+ 字号调节 |
| 图片 | `ImagePreview` | 缩放（0.1x-10x）、拖拽平移、适应窗口、双击切换 100%/适应 |
| PDF | `PdfPreview` | 翻页、缩放（0.5x-5x）、Ctrl+滚轮缩放 |
| Word | `WordPreview` | python-docx → HTML，标题/加粗/斜体/下划线/表格 |
| Excel | `ExcelPreview` | openpyxl → HTML 表格，最多 500 行，交替行色 |
| PPT | `PptPreview` | PowerPoint COM → PNG（1920×1080），逐页导航 |
| Markdown | `MarkdownPreview` | 代码块/表格/引用/标题，暗色 CSS |

### 3.2 工具栏按钮（按类型动态显示）

关闭 / 标题 / 缩放控件 / 翻页控件 / 复制 / 用默认程序打开 / 全屏

### 3.3 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Escape` | 退出全屏 / 关闭 |
| `F11` | 切换全屏 |
| `←` / `PageUp` | 上一页/上一张幻灯片 |
| `→` / `PageDown` | 下一页/下一张幻灯片 |
| `Home` / `End` | 首页/末页 |
| `+` / `-` | 放大/缩小 |
| `Ctrl+滚轮` | 缩放（图片/PDF） |

---

## 4. 系统托盘 — `TrayIcon.py`

**入口**：`src/app.py` → `src/ui/tray_icon.py`  
**图标**：`assets/icons/tray-icon.png`，右下角状态点  
**提示文本**：`拾遗 - [在线/警告/错误/离线] | Ctrl+Shift+V 唤出`

### 4.1 托盘菜单

| 菜单项 | 功能 |
|--------|------|
| 显示面板 | 切换主面板显示 |
| 打开详情面板 | 同上 |
| 显示/隐藏悬浮球 | 切换悬浮球可见性 |
| 暂停剪贴板监听 | 开/关监听，系统通知提示 |
| ── 数据管理 ── | |
| 导出 JSON | 文件保存对话框 → 导出 |
| 导入 JSON | 文件选择对话框 → 导入 |
| 导出 CSV | 文件保存对话框 → 导出 |
| 导入 CSV | 文件选择对话框 → 导入 |
| ── 存储模式 ── | |
| [V] 临时模式 | 切换后需重启 |
| [D] 持久模式 | 切换后需重启 |
| ── | |
| 开机自启 | 写入 Windows 注册表 |
| 退出 | 关闭程序 |

**交互**：双击托盘图标 → 切换主面板

---

## 5. 全局热键 — `global_hotkey.py`

**实现**：Windows `RegisterHotKey` API + `QAbstractNativeEventFilter`

| 热键 | 功能 |
|------|------|
| `Ctrl+Shift+V` | 切换主面板显示/隐藏 |
| `Ctrl+Shift+C` | 截取选区：保存剪贴板 → 模拟 Ctrl+C → 读取新内容 → 导入 → 还原原剪贴板 |

---

## 6. 导出对话框 — `ExportDialog.py`

**入口**：多选操作栏"导出" / 托盘菜单  
**五种导出方式**（单选）：

| 方式 | 说明 |
|------|------|
| 合并写入剪贴板 | 文本内容以 `---` 分隔合并 |
| 复制文件路径到剪贴板 | 文件 URL 列表 |
| 导出到指定文件夹 | 复制文件到用户选择的目录 |
| 打包为 .zip 文件 | 创建 ZIP 压缩包 |
| 发送到预览栏 | 发送到悬浮球预览栏供拖出 |

智能默认：纯文本→剪贴板，纯文件→文件夹，混合→预览栏。

---

## 7. 标签管理对话框 — `TagDialog.py`

**入口**：标签栏 `+` 按钮（PyQt6 版）  
**规格**：420×480px，暗色主题

- 顶部：名称输入（最多 20 字符）+ 颜色选择器 + 添加按钮
- 列表：每个标签显示颜色点 + 名称 + 编辑 + 删除
- 编辑：弹出输入对话框 + 颜色对话框
- 删除：确认对话框
- 上限 100 个标签

---

## 8. 设计系统

### 8.1 QML 主题 — `ThemeSingleton.py`

曜石青暗色主题，通过 `pyqtProperty` 暴露给 QML：

| 分类 | 关键值 |
|------|--------|
| 背景 | `#080B0F` → `#10161C` → `#172029` → `#0C1116`（面板） |
| 文字 | `#F0F5F2`（主）/ `#A8B3BD`（次）/ `#71808F`（三级） |
| 强调色 | 薄荷绿 `#7CE0C3` / 青色 `#66B8C7` / 警告黄 `#F2B84B` |
| 文件类型 | Word 蓝 / Excel 绿 / PDF 红 / PPT 黄 / 压缩紫 / 图片薄荷 |
| 字体 | Microsoft YaHei + Segoe UI |
| 圆角 | SM=6 / MD=10 / LG=14 |

### 8.2 PyQt6 设计系统 — `design_system.py`

为 PyQt6 原生控件提供样式模板：QLineEdit / QPushButton / QListView / QComboBox / QMenu。

---

## 9. 窗口特效 — `acrylic.py`

| 系统 | 特效 |
|------|------|
| Windows 11 (22000+) | Mica 云母效果 |
| Windows 10 1809+ (17763+) | Acrylic 亚克力效果 |

---

## 10. 数据流概览

```
系统剪贴板 → ClipboardManager → Database → FastAPI Server
                                                ↓ (WebSocket)
                                          ApiClient
                                                ↓
                                    QmlBridge + QClipboardListModel
                                                ↓
                                          QML 主面板
                                          
悬浮球 ← PreviewBar ← api_client.items_changed 信号
托盘 ← TrayIcon ← api_client.status_changed 信号
预览窗口 ← PreviewWindow ← bridge.previewRequested 信号
```

---

## 11. REST API 端点总览

基础地址：`http://127.0.0.1:8199`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 状态/计数/容量/存储模式 |
| GET | `/api/items` | 列表查询（分页/筛选/搜索） |
| GET | `/api/items/search` | 关键词搜索 |
| POST | `/api/items/{id}/copy` | 复制到剪贴板 |
| DELETE | `/api/items/{id}` | 删除单条 |
| POST | `/api/items/{id}/pin` | 切换置顶 |
| POST | `/api/items/{id}/favorite` | 切换收藏 |
| POST | `/api/items/{id}/star` | 切换星标 |
| POST | `/api/items/batch-delete` | 批量删除 |
| POST | `/api/items/paste` | 从剪贴板粘贴导入 |
| POST | `/api/items/merge` | 合并多条 |
| POST | `/api/items/clear` | 清空全部 |
| POST | `/api/items/import` | 导入文件 |
| POST | `/api/items/import-text` | 导入文本 |
| GET/POST | `/api/config` | 读取/更新配置 |
| POST | `/api/config/clipboard-enabled` | 开关监听 |
| GET/POST | `/api/projects` | 项目管理 |
| GET/POST/PUT/DELETE | `/api/tags` | 标签 CRUD |
| POST/DELETE | `/api/items/{id}/tags` | 条目标签关联 |
| WS | `/ws` | 实时 `items-changed` 推送 |
