/**
 * 渲染器模块
 * 数据绑定 + 剪贴板列表 + 动画效果
 */

class Renderer {
  constructor() {
    this._stateMachine = new window.StateMachine();
    this._panelVisible = false;
    this._items = [];
    this._searchTimer = null;

    this._elements = {
      icon: document.querySelector('.bar-icon'),
      statusText: document.getElementById('statusText'),
      statusCount: document.getElementById('statusCount'),
      indicator: document.getElementById('statusIndicator'),
      panel: document.getElementById('clipboardPanel'),
      list: document.getElementById('clipboardList'),
      searchInput: document.getElementById('searchInput'),
      clearBtn: document.getElementById('clearBtn'),
      floatingBar: document.getElementById('floatingBar'),
    };

    this._init();
  }

  _init() {
    // 监听状态变化
    this._stateMachine.onStateChange((newState) => {
      this._updateStatusUI(newState);
    });

    // 监听主进程数据更新
    window.electronAPI.onDataUpdate((data) => {
      this._handleDataUpdate(data);
    });

    // 监听状态变化
    window.electronAPI.onStateChange((state) => {
      this._stateMachine.transition(state);
    });

    // 监听新条目推送
    window.electronAPI.onNewItem?.((data) => {
      this._loadItems();
    });

    // 悬浮条点击展开/收起面板
    this._elements.floatingBar.addEventListener('click', (e) => {
      // 排除拖拽
      if (e.target.closest('.bar-status') || e.target.closest('.bar-icon')) {
        this._togglePanel();
      }
    });

    // 搜索框
    this._elements.searchInput.addEventListener('input', () => {
      clearTimeout(this._searchTimer);
      this._searchTimer = setTimeout(() => this._doSearch(), 300);
    });

    // 清空按钮
    this._elements.clearBtn.addEventListener('click', async () => {
      await window.electronAPI.clearItems();
      this._loadItems();
    });

    // 初始状态
    this._updateStatusUI(this._stateMachine.currentState);

    // 加载初始数据
    this._loadItems();

    // v3.0 拖拽收录
    this._initDropZone();
  }

  _updateStatusUI(state) {
    const config = window.STATE_CONFIG[state];
    if (!config) return;

    const { icon, statusText, indicator } = this._elements;

    if (icon) icon.textContent = config.icon;
    if (statusText) statusText.textContent = config.text;

    if (indicator) {
      indicator.classList.remove('online', 'warning', 'error', 'offline', 'pulse');
      indicator.classList.add(state);
      if (config.pulse) indicator.classList.add('pulse');
    }
  }

  _handleDataUpdate(data) {
    const { count, status, message } = data;

    if (count !== undefined && this._elements.statusCount) {
      this._elements.statusCount.textContent = `${count} 条`;
    }

    if (status) {
      this._stateMachine.transition(status);
    }

    if (message) {
      window.NotificationManager?.show(message);
    }

    // 自动刷新列表（如果面板打开）
    if (this._panelVisible) {
      this._loadItems();
    }
  }

  _togglePanel() {
    this._panelVisible = !this._panelVisible;
    this._elements.panel.classList.toggle('visible', this._panelVisible);

    if (this._panelVisible) {
      this._loadItems();
      // 调整窗口高度
      this._resizeWindow(450);
      this._elements.searchInput.focus();
    } else {
      this._resizeWindow(46);
    }
  }

  async _resizeWindow(height) {
    // 通过 IPC 通知主进程调整窗口大小
    // 这里简化处理，实际可通过 ipcRenderer.send('resize-window', height)
  }

  async _loadItems() {
    try {
      const result = await window.electronAPI.getItems(50);
      this._items = result.items || [];
      this._renderItems(this._items);
    } catch (e) {
      console.error('Failed to load items:', e);
    }
  }

  async _doSearch() {
    const query = this._elements.searchInput.value.trim();
    if (!query) {
      this._loadItems();
      return;
    }

    try {
      const result = await window.electronAPI.searchItems(query);
      this._renderItems(result.items || []);
    } catch (e) {
      console.error('Search failed:', e);
    }
  }

  _renderItems(items) {
    const list = this._elements.list;
    if (!list) return;

    if (items.length === 0) {
      list.innerHTML = '<div class="empty-hint">暂无记录</div>';
      return;
    }

    list.innerHTML = items.map(item => this._renderItem(item)).join('');

    // 绑定事件
    list.querySelectorAll('.clipboard-item').forEach(el => {
      const id = parseInt(el.dataset.id);

      el.addEventListener('click', async (e) => {
        if (e.target.closest('.item-action-btn')) return;
        await window.electronAPI.copyItem(id);
        window.NotificationManager?.show('已复制到剪贴板');
      });

      el.querySelector('.btn-pin')?.addEventListener('click', async () => {
        await window.electronAPI.pinItem(id);
        this._loadItems();
      });

      el.querySelector('.btn-delete')?.addEventListener('click', async () => {
        await window.electronAPI.deleteItem(id);
        this._loadItems();
      });
    });
  }

  _renderItem(item) {
    const icon = this._getTypeIcon(item.content_type);
    const preview = this._getPreview(item);
    const time = this._formatTime(item.created_at);
    const pinnedClass = item.is_pinned ? 'pinned' : '';

    return `
      <div class="clipboard-item ${pinnedClass}" data-id="${item.id}">
        <div class="item-icon">${icon}</div>
        <div class="item-content">
          <div class="item-preview">${this._escapeHtml(preview)}</div>
          <div class="item-meta">${time}</div>
        </div>
        <div class="item-actions">
          <button class="item-action-btn btn-pin" title="${item.is_pinned ? '取消置顶' : '置顶'}">
            ${item.is_pinned ? '📌' : '📍'}
          </button>
          <button class="item-action-btn btn-delete" title="删除">✕</button>
        </div>
      </div>
    `;
  }

  _getTypeIcon(type) {
    const icons = { TEXT: '📝', IMAGE: '🖼️', FILES: '📁', HTML: '🌐' };
    return icons[type] || '📝';
  }

  _getPreview(item) {
    if (item.content_type === 'TEXT' || item.content_type === 'HTML') {
      return (item.content_text || '').substring(0, 80).replace(/\n/g, ' ');
    }
    if (item.content_type === 'IMAGE') return '[图片]';
    if (item.content_type === 'FILES') return `[文件] ${item.content_text || ''}`;
    return '';
  }

  _formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    const diff = now - d;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    return d.toLocaleDateString('zh-CN');
  }

  _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // v3.0 拖拽收录
  _initDropZone() {
    const overlay = document.getElementById('dropZoneOverlay');
    if (!overlay) return;

    let dragCount = 0;

    document.addEventListener('dragenter', (e) => {
      e.preventDefault();
      dragCount++;
      overlay.classList.add('active');
    });

    document.addEventListener('dragover', (e) => {
      e.preventDefault();
    });

    document.addEventListener('dragleave', (e) => {
      e.preventDefault();
      dragCount--;
      if (dragCount <= 0) {
        dragCount = 0;
        overlay.classList.remove('active');
      }
    });

    document.addEventListener('drop', (e) => {
      e.preventDefault();
      dragCount = 0;
      overlay.classList.remove('active');

      const files = Array.from(e.dataTransfer.files).map(f => f.path).filter(Boolean);
      if (files.length > 0) {
        window.electronAPI.importFiles(files, 'drag-drop');
        window.electronAPI.showNotification?.(`已收录 ${files.length} 个文件`);
      }
    });
  }
}

// 初始化渲染器
new Renderer();
