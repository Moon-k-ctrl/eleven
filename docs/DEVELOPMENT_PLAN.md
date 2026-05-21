# 拾遗 开发计划

> **版本**: v3.2.0 规划  
> **日期**: 2026-05-18  
> **状态**: 待启动

---

## 项目现状总览

### 已完成 (Done)

| 模块 | 状态 | 说明 |
|------|------|------|
| 剪贴板监听 | ✅ | Win32 `WM_CLIPBOARDUPDATE`，支持文本/图片/文件/HTML |
| 核心管理器 | ✅ | `ClipboardManager` 474 行，CRUD + 标签 + 项目 + 搜索 |
| 数据库 | ✅ | `Database` 730 行，SQLite + FTS5，双存储模式 |
| 配置系统 | ✅ | `Config` 144 行，JSON 持久化 |
| REST API | ✅ | 28 个端点 + WebSocket 实时推送 |
| QML 主面板 | ✅ | 14 个组件，暗色曜石青主题 |
| 悬浮球/预览栏 | ✅ | `PreviewBar` 871 行，球↔栏形变动画 |
| 系统托盘 | ✅ | 完整菜单，导入导出，存储模式切换 |
| 预览窗口 | ✅ | 7 种格式：文本/图片/Word/Excel/PDF/PPT/Markdown |
| 全局热键 | ✅ | `Ctrl+Shift+V` 面板 / `Ctrl+Shift+C` 截取 |
| 文档 | ✅ | PRD / ARCHITECTURE / UI_SCREENS / CODE_WIKI |
| Electron 清理 | ✅ | 所有过时引用已清除 |

### 待改进 (Gaps)

| 类别 | 问题 | 优先级 |
|------|------|--------|
| 设计对齐 | 主题色值与设计稿有偏差（accent-green #5CD4B0 vs #54D49E） | P1 |
| 设计对齐 | 缺少 surface-0/1/2、line-soft/strong、shadow-soft/pop token | P1 |
| 设计对齐 | 文件类型图标颜色需更新（text=#9FCBFF, word=#9EDDE8 等） | P1 |
| 设计对齐 | 悬浮球渐变样式未对齐设计稿 | P2 |
| 测试覆盖 | 仅 32 个测试，覆盖 model/database/tag，无 API/UI 测试 | P1 |
| 测试覆盖 | 无 Win32 API mock，无法 CI 测试 | P2 |
| 代码清理 | 6 个 legacy PyQt6 文件仍在（floating_panel/delegate/model 等） | P2 |
| 功能缺口 | TagBar `+` 按钮未接标签管理对话框（TODO） | P2 |
| 功能缺口 | 上下文菜单缺少"发送到预览栏"选项 | P2 |
| 功能缺口 | 导出对话框（ExportDialog.py）仅托盘菜单可用，面板内未接入 | P3 |
| 构建打包 | PyInstaller spec 需验证 QML 打包完整性 | P2 |

---

## 开发阶段

### Phase 1: 设计系统对齐 (Design System Alignment)

**目标**: QML UI 完全匹配设计稿 `拾遗完整UI设计系统-新版配色代码.md`

**分工**: @ui-agent

#### 1.1 主题色值更新 — `theme_singleton.py`

| 属性 | 当前值 | 目标值 | 说明 |
|------|--------|--------|------|
| `accentHover` | `#5CD4B0` | `#54D49E` | 设计稿 accent-green |
| `accentGold` | `#F2B84B` | `#F2B84B` | 不变 |
| `typeText` | `#F0F5F2` | `#9FCBFF` | 设计稿 text-icon |
| `typeWord` | `#66B8C7` | `#9EDDE8` | 设计稿 word-icon |
| `typeExcel` | `#5CD4B0` | `#54D49E` | 设计稿 excel-icon |
| `typePdf` | `#F06464` | `#FF9A9A` | 设计稿 pdf-icon |
| `typePpt` | `#F2B84B` | `#FFD98A` | 设计稿 ppt-icon |
| `typeArchive` | `#A888D8` | `#A8B3BD` | 设计稿 zip-icon |

新增属性：

```python
# Surface layers
surface0 = "rgba(8, 11, 15, 0.98)"    # 最深层
surface1 = "rgba(16, 22, 28, 0.92)"   # 卡片/面板
surface2 = "rgba(24, 33, 41, 0.86)"   # 弹出层

# Lines
lineSoft = "rgba(225, 238, 231, 0.08)"    # 普通边框
lineStrong = "rgba(225, 238, 231, 0.16)"  # 强调边框

# Shadows
shadowSoft = "0 18px 54px rgba(0, 0, 0, 0.38)"
shadowPop = "0 12px 28px rgba(84, 212, 158, 0.18)"

# Panel header
bgPanelHeader = "#071016"
```

#### 1.2 组件样式更新

| 组件 | 文件 | 改动 |
|------|------|------|
| TitleBar | `TitleBar.qml` | header 背景改 `bgPanelHeader`，使用 `lineSoft` 边框 |
| SearchBar | `SearchBar.qml` | 背景 `surface1`，边框 `lineSoft`，focus 用 `accentMint` |
| FilterBar | `CategoryButton.qml` | 激活态用 `accentMint` 背景 |
| TagChip | `TagChip.qml` | 激活态金色 `#FFD98A` + `rgba(242,184,75,0.12)` 背景 |
| ClipboardItemDelegate | `ClipboardItemDelegate.qml` | hover 用 `rgba(124,224,195,0.075)`，边框 `rgba(124,224,195,0.18)` |
| FileTypeIcon | `FileTypeIcon.qml` | 颜色对齐上述 type 属性值 |
| 上下文菜单 | `ClipboardItemDelegate.qml` | 新增"发送到预览栏"菜单项 |
| EmptyState | `EmptyState.qml` | 使用 `textTertiary` |
| DropOverlay | `DropOverlay.qml` | 使用 `accentMint` 虚线 |

#### 1.3 悬浮球样式更新 — `preview_bar.py`

- 球体渐变：`linear-gradient(135deg, accentMint, accentBlue)` → 用 `QLinearGradient` 实现
- 阴影：`0 18px 40px rgba(84,212,158,0.28)`
- 高光：`inset 0 1px 0 rgba(255,255,255,0.2)`

**验收标准**:
- [ ] `python -m src.app` 启动无 QML 错误
- [ ] 所有颜色值与设计稿一致
- [ ] 悬浮球显示渐变效果
- [ ] 上下文菜单包含"发送到预览栏"

---

### Phase 2: 测试补全 (Test Coverage)

**目标**: 测试覆盖率 ≥ 80%

**分工**: @qa-agent

#### 2.1 API 测试 — `tests/test_api.py` (新建)

使用 `httpx.AsyncClient` + `TestClient` 测试 FastAPI 端点：

| 测试组 | 测试用例 |
|--------|----------|
| `/api/status` | 返回 200，包含 status/count/max_items/storage_mode |
| `/api/items` | 分页、cursor、category 筛选、tag 筛选 |
| `/api/items/search` | 关键词搜索、空结果 |
| `/api/items/{id}/copy` | 正常复制、不存在的 ID |
| `/api/items/{id}` DELETE | 删除、不存在 |
| `/api/items/{id}/pin` | 切换置顶 |
| `/api/items/{id}/favorite` | 切换收藏 |
| `/api/items/{id}/star` | 切换星标 |
| `/api/items/batch-delete` | 批量删除 |
| `/api/items/merge` | 合并多条 |
| `/api/items/clear` | 清空 |
| `/api/items/import` | 导入文件 |
| `/api/items/import-text` | 导入文本 |
| `/api/tags` CRUD | 创建、列表、更新、删除 |
| `/api/items/{id}/tags` | 添加/移除标签 |
| `/api/projects` CRUD | 创建、列表、删除 |
| `/api/config` GET/POST | 读取/更新配置 |
| WebSocket `/ws` | 连接、items-changed 推送 |

预计 ~40 个测试用例。

#### 2.2 Manager 测试 — `tests/test_manager.py` (新建)

| 测试组 | 测试用例 |
|--------|----------|
| `import_files()` | 文本文件、图片文件、多文件、空列表 |
| `copy_to_clipboard()` | 文本、文件路径 |
| `toggle_pin/favorite/star()` | 切换状态 |
| `clear_all()` | 清空 + 容量检查 |
| `merge_items()` | 合并文本、合并文件 |
| `search_with_filters()` | 组合查询+标签+分类 |
| `_read_clipboard()` | 各种格式读取（需 mock Win32） |
| `paste_from_clipboard()` | 粘贴导入 |

预计 ~25 个测试用例。需 mock `win32clipboard`。

#### 2.3 Config 测试 — `tests/test_config.py` (新建)

| 测试用例 |
|----------|
| 默认配置值 |
| 持久化读写 |
| 存储模式切换 |
| 球位置保存/读取 |
| 无效配置文件处理 |

预计 ~10 个测试用例。

#### 2.4 工具函数测试 — `tests/test_utils.py` (新建)

| 测试组 | 测试用例 |
|--------|----------|
| `import_export.py` | JSON 导出/导入、CSV 导出/导入 |
| `autostart.py` | 注册表操作（需 mock） |
| `helpers.py` | 辅助函数 |

预计 ~15 个测试用例。

#### 2.5 Win32 Mock 基础设施 — `tests/conftest.py`

```python
@pytest.fixture
def mock_win32clipboard(monkeypatch):
    """Mock win32clipboard for CI environments."""
    ...

@pytest.fixture
def mock_win32api(monkeypatch):
    """Mock win32api for registry operations."""
    ...
```

**验收标准**:
- [ ] `pytest --cov=src --cov-report=term-missing` 总覆盖率 ≥ 80%
- [ ] 所有测试在无 Win32 环境下可运行（mock）
- [ ] 无 flaky 测试

---

### Phase 3: 功能补全 (Feature Completion)

**目标**: 补齐 TODO 和功能缺口

**分工**: @ui-agent + @core-agent

#### 3.1 标签管理对话框接入 — @ui-agent

**文件**: `TagBar.qml` 的 `+` 按钮

- 创建 QML 版标签管理弹窗（或通过 bridge 调用 Python TagDialog）
- 功能：查看所有标签、创建/编辑/删除、颜色选择
- 接入 `bridge.createTag()` / `bridge.getAllTags()`

#### 3.2 "发送到预览栏" 功能 — @ui-agent + @core-agent

- 上下文菜单新增选项
- 通过 bridge 调用 `preview_bar.add_items()`
- PreviewBar 需暴露接收方法

#### 3.3 Legacy 文件清理 — @ui-agent

以下 PyQt6 原生文件已被 QML 版本替代，可标记为 legacy 或删除：

| 文件 | 状态 | 建议 |
|------|------|------|
| `clipboard_item_delegate.py` | 被 QML delegate 替代 | 移至 `_legacy/` |
| `clipboard_item_widget.py` | 被 QML delegate 替代 | 移至 `_legacy/` |
| `clipboard_list_model.py` | 被 `QClipboardListModel` 替代 | 移至 `_legacy/` |
| `floating_panel.py` | 被 QML main panel 替代 | 移至 `_legacy/` |
| `tag_chip.py` | 被 QML TagChip 替代 | 移至 `_legacy/` |
| `drag_handler.py` | 功能已内嵌 QML | 移至 `_legacy/` |

> 注意：`floating_ball.py`、`preview_bar.py`、`tray_icon.py`、`preview_window.py` 仍在使用，不可清理。

#### 3.4 导出对话框面板内接入 — @ui-agent

- TitleBar "导出" 按钮当前仅触发 JSON 导出
- 需接入 `ExportDialog.py` 的完整五种导出方式
- 通过 bridge 暴露 `showExportDialog()` slot

**验收标准**:
- [ ] 标签栏 `+` 按钮打开标签管理
- [ ] 右键菜单可"发送到预览栏"
- [ ] Legacy 文件已隔离
- [ ] 导出按钮打开完整导出对话框

---

### Phase 4: 构建与发布 (Build & Release)

**目标**: 可分发的安装包

**分工**: @devops-agent

#### 4.1 PyInstaller Spec 更新

- 验证 QML 文件打包（`src/ui/qml/` 目录）
- 验证 assets 打包（图标、字体）
- 测试 `--onefile` 和 `--onedir` 两种模式

#### 4.2 安装包制作

- Inno Setup / NSIS 安装向导
- 开机自启注册
- 卸载清理

#### 4.3 CI/CD (可选)

- GitHub Actions：lint + test + build
- 自动发布到 Releases

**验收标准**:
- [ ] `pyinstaller eleven.spec` 成功构建
- [ ] 构建产物在无 Python 环境下可运行
- [ ] QML 面板、悬浮球、托盘均正常

---

## 任务分配矩阵

| 任务 | Phase | Agent | 预估工时 | 依赖 |
|------|-------|-------|----------|------|
| 主题色值对齐 | 1 | @ui-agent | 2h | — |
| 新增 surface/line/shadow token | 1 | @ui-agent | 1h | — |
| 组件样式更新（9 个 QML） | 1 | @ui-agent | 3h | 色值对齐 |
| 悬浮球渐变样式 | 1 | @ui-agent | 1h | — |
| 上下文菜单新增项 | 1 | @ui-agent | 0.5h | — |
| API 测试 | 2 | @qa-agent | 4h | — |
| Manager 测试 | 2 | @qa-agent | 3h | Win32 mock |
| Config 测试 | 2 | @qa-agent | 1h | — |
| Utils 测试 | 2 | @qa-agent | 1.5h | — |
| Win32 mock 基础设施 | 2 | @qa-agent | 1h | — |
| 标签管理对话框 | 3 | @ui-agent | 2h | — |
| 发送到预览栏 | 3 | @ui-agent + @core-agent | 1.5h | — |
| Legacy 文件清理 | 3 | @ui-agent | 0.5h | — |
| 导出对话框接入 | 3 | @ui-agent | 1.5h | — |
| PyInstaller spec | 4 | @devops-agent | 2h | Phase 1-3 |
| 安装包制作 | 4 | @devops-agent | 2h | spec 验证 |

**总预估工时**: ~27h

---

## 执行顺序

```
Phase 1 (设计对齐) ──→ Phase 2 (测试补全) ──→ Phase 3 (功能补全) ──→ Phase 4 (构建发布)
      │                      │                      │
      ├─ 可并行 ─────────────┤                      │
      │                      ├─ 可并行 ─────────────┤
      └──────────────────────┴──────────────────────┘
```

- Phase 1 和 Phase 2 可并行执行（UI 改动 vs 测试编写互不阻塞）
- Phase 3 依赖 Phase 1 的 UI 组件更新
- Phase 4 依赖所有前置 Phase

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| QML 打包后路径解析失败 | 面板无法加载 | 提前验证 `sys._MEIPASS` 路径 |
| Win32 mock 不完整 | CI 测试遗漏 | 优先实现 clipboard mock |
| 设计稿色值与实际渲染偏差 | UI 不一致 | 截图对比 + 调整 |
| Legacy 文件有隐式依赖 | 清理后报错 | grep 确认无 import 后再移除 |

---

## 里程碑

| 里程碑 | 包含 Phase | 目标日期 |
|--------|-----------|----------|
| M1: UI 设计对齐 | Phase 1 | — |
| M2: 测试覆盖 80% | Phase 2 | — |
| M3: 功能完整 | Phase 3 | — |
| M4: v3.2.0 发布 | Phase 4 | — |
