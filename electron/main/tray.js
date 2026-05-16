/**
 * 系统托盘模块
 * 创建托盘图标和右键菜单
 */

const { Tray, Menu, nativeImage, BrowserWindow, app } = require('electron');
const path = require('path');

class TrayManager {
  constructor(mainWindow, dashboardWindow, floatingBall) {
    this._tray = null;
    this._mainWindow = mainWindow;
    this._dashboardWindow = dashboardWindow;
    this._floatingBall = floatingBall;
    this._init();
  }

  _init() {
    // 创建托盘图标
    const iconPath = path.join(__dirname, '..', 'assets', 'icons', 'icon.png');
    let icon;

    try {
      icon = nativeImage.createFromPath(iconPath);
      if (icon.isEmpty()) {
        icon = nativeImage.createEmpty();
      }
    } catch {
      icon = nativeImage.createEmpty();
    }

    this._tray = new Tray(icon);
    this._tray.setToolTip('拾遗 - Ctrl+Shift+H 唤出');

    // 创建右键菜单
    this._updateContextMenu();

    // 双击托盘显示悬浮条
    this._tray.on('double-click', () => {
      this._toggleWindow();
    });

    // 右键点击时更新菜单（反映当前窗口状态）
    this._tray.on('right-click', () => {
      this._updateContextMenu();
    });
  }

  _updateContextMenu() {
    const isVisible = this._mainWindow && !this._mainWindow.isDestroyed() && this._mainWindow.isVisible();

    const contextMenu = Menu.buildFromTemplate([
      {
        label: isVisible ? '隐藏悬浮条' : '显示悬浮条',
        click: () => this._toggleWindow()
      },
      { type: 'separator' },
      {
        label: '打开详情面板',
        click: () => this._openDashboard()
      },
      {
        label: '显示/隐藏悬浮球',
        click: () => {
          if (this._floatingBall) {
            this._floatingBall.toggle();
          }
        }
      },
      { type: 'separator' },
      {
        label: '退出',
        click: () => app.quit()
      }
    ]);

    this._tray.setContextMenu(contextMenu);
  }

  _toggleWindow() {
    if (!this._mainWindow || this._mainWindow.isDestroyed()) return;

    if (this._mainWindow.isVisible()) {
      this._mainWindow.hide();
    } else {
      this._mainWindow.show();
    }
    this._updateContextMenu();
  }

  _openDashboard() {
    if (this._dashboardWindow && !this._dashboardWindow.isDestroyed()) {
      this._dashboardWindow.open(this._mainWindow);
    }
  }

  setDashboardWindow(dashboardWindow) {
    this._dashboardWindow = dashboardWindow;
  }

  destroy() {
    if (this._tray) {
      this._tray.destroy();
      this._tray = null;
    }
  }
}

module.exports = TrayManager;
