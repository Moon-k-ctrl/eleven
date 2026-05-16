/**
 * FloatingBallWindow — 悬浮球窗口
 * 80x80 透明窗口，32px 可见圆，支持拖拽收录和位置记忆
 */
const { BrowserWindow, screen, ipcMain } = require('electron');
const path = require('path');

class FloatingBallWindow {
  /**
   * @param {Object} options
   * @param {import('electron-store')} options.store - electron-store instance
   * @param {string} options.apiUrl - Python backend URL
   */
  constructor(options = {}) {
    this._window = null;
    this._store = options.store;
    this._apiUrl = options.apiUrl || 'http://127.0.0.1:8199';
    this._badgeCount = 0;
  }

  create() {
    const display = screen.getPrimaryDisplay();
    const { width: screenW, height: screenH } = display.workAreaSize;

    // 读取保存的位置，默认右下角
    let savedPos = null;
    try {
      savedPos = this._store?.get('floatingBallPosition');
    } catch {}

    const defaultX = screenW - 100;
    const defaultY = screenH - 100;

    this._window = new BrowserWindow({
      width: 80,
      height: 80,
      x: savedPos ? savedPos[0] : defaultX,
      y: savedPos ? savedPos[1] : defaultY,
      transparent: true,
      frame: false,
      alwaysOnTop: true,
      skipTaskbar: true,
      resizable: false,
      focusable: false,
      hasShadow: false,
      webPreferences: {
        preload: path.join(__dirname, '..', 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    this._window.loadFile(path.join(__dirname, '..', 'floating-ball.html'));
    this._window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

    // 穿透透明区域，只响应可见圆部分
    // 注意：拖拽文件时需要关闭穿透，否则 drop 事件不触发
    this._window.setIgnoreMouseEvents(true, { forward: true });

    // 监听渲染进程的鼠标进入/离开事件（用于切换穿透状态）
    ipcMain.on('ball-mouse-enter', () => {
      if (this._window && !this._window.isDestroyed()) {
        this._window.setIgnoreMouseEvents(false);
      }
    });
    ipcMain.on('ball-mouse-leave', () => {
      if (this._window && !this._window.isDestroyed()) {
        this._window.setIgnoreMouseEvents(true, { forward: true });
      }
    });

    // 拖拽时关闭穿透（通过 IPC）
    ipcMain.on('ball-drag-enter', () => {
      if (this._window && !this._window.isDestroyed()) {
        this._window.setIgnoreMouseEvents(false);
      }
    });
    ipcMain.on('ball-drag-leave', () => {
      if (this._window && !this._window.isDestroyed()) {
        this._window.setIgnoreMouseEvents(true, { forward: true });
      }
    });

    // 保存位置
    this._window.on('moved', () => {
      if (this._window && !this._window.isDestroyed()) {
        const pos = this._window.getPosition();
        try {
          this._store?.set('floatingBallPosition', pos);
        } catch {}
      }
    });
  }

  updateBadge(count) {
    this._badgeCount = count;
    if (this._window && !this._window.isDestroyed()) {
      this._window.webContents.send('badge-update', { count });
    }
  }

  show() {
    if (this._window && !this._window.isDestroyed()) {
      this._window.show();
    }
  }

  hide() {
    if (this._window && !this._window.isDestroyed()) {
      this._window.hide();
    }
  }

  toggle() {
    if (!this._window || this._window.isDestroyed()) return;
    if (this._window.isVisible()) {
      this._window.hide();
    } else {
      this._window.show();
    }
  }

  destroy() {
    if (this._window && !this._window.isDestroyed()) {
      this._window.close();
    }
    this._window = null;
  }
}

module.exports = FloatingBallWindow;
