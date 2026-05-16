/**
 * 详情面板窗口管理
 * 独立窗口展示完整数据
 */

const { BrowserWindow } = require('electron');
const path = require('path');

class DashboardWindow {
  constructor() {
    this._window = null;
  }

  open(parentWindow) {
    if (this._window && !this._window.isDestroyed()) {
      this._window.focus();
      return;
    }

    // 获取父窗口位置
    const parentBounds = parentWindow.getBounds();

    this._window = new BrowserWindow({
      width: 600,
      height: 500,
      x: parentBounds.x + parentBounds.width + 10,
      y: parentBounds.y,
      title: 'eleven - 详情面板',
      show: false,
      webPreferences: {
        preload: path.join(__dirname, '..', 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false
      }
    });

    this._window.loadFile('dashboard.html');

    this._window.once('ready-to-show', () => {
      this._window.show();
    });

    this._window.on('closed', () => {
      this._window = null;
    });
  }

  close() {
    if (this._window && !this._window.isDestroyed()) {
      this._window.close();
    }
  }

  isOpen() {
    return this._window && !this._window.isDestroyed();
  }
}

module.exports = DashboardWindow;
