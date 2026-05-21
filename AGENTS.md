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

## Server Mode (with QML UI)
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
  ui/             # PyQt6/QML 面板、悬浮球、托盘
  models/         # 数据模型
  utils/          # 工具函数
tests/            # 测试
docs/             # PRD、架构文档
```

## Conventions
- 中文注释可以，docstring 用英文
- 必须加 type hints
- 当前阶段：MVP（仅 P0 功能）
- 核心数据流：系统剪贴板 → Listener → Manager → Database → UI

---

## Multi-Agent Collaboration Guide

> **Version**: 1.0.0 | **Created**: 2026-05-18

### Agent Roles

| Agent | Role | Responsibilities |
|-------|------|-----------------|
| @manager-agent | Project Manager | 需求拆解、任务分配、协调冲突、架构决策、DoD 审核 |
| @rust-agent | Rust Developer | 系统级编程、性能优化、内存安全、WebAssembly |
| @frontend-agent | Frontend Developer | UI 组件、客户端逻辑、响应式设计、a11y |
| @devops-agent | DevOps Engineer | CI/CD、容器化、云基础设施、监控告警 |
| @qa-agent | QA Engineer | 测试自动化、Bug 验证、回归测试、覆盖率 |
| @docs-agent | Documentation | README、API 文档、用户指南、Changelog |

### Collaboration Protocols

**异步协作（推荐）**：通过 PR + Issue 沟通，Agent 独立工作，PR 评审后合并。

**同步协作（复杂功能）**：共享分支、Pair Programming、频繁 `@mention` 沟通。

**冲突解决**：
```
Agent ↔ Agent 直接讨论
    ↓ (未解决)
@manager-agent 决策
    ↓ (仍有争议)
Human Oversight 最终裁决
```

### Git Commit Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

### Code Review Checklist

- [ ] 功能正确性
- [ ] 测试充分且通过
- [ ] 文档/注释清晰
- [ ] 符合项目风格
- [ ] 无明显性能问题
- [ ] 无安全隐患
- [ ] 边界/错误处理
- [ ] 新依赖合理
- [ ] Breaking Changes 已记录

### Definition of Done (DoD)

- [ ] 代码实现并通过所有测试
- [ ] 至少一位 Agent 审核通过
- [ ] 文档已更新
- [ ] CI/CD 无阻塞
- [ ] staging 环境验证通过

### Agent Selection Cheat Sheet

| 任务 | 分配给 |
|------|--------|
| 新功能规划 | @manager-agent |
| 系统级代码、性能优化 | @rust-agent |
| UI 组件、前端逻辑 | @frontend-agent |
| CI/CD、部署、基础设施 | @devops-agent |
| 测试、自动化、Bug 验证 | @qa-agent |
| 文档、API docs、指南 | @docs-agent |
| 跨模块协调 | @manager-agent |
