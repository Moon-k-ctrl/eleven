/**
 * 全局快捷键模块
 * 注册和管理全局快捷键
 */

const { globalShortcut, clipboard, nativeImage, app } = require('electron');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

class ShortcutManager {
  /**
   * @param {BrowserWindow} mainWindow
   * @param {DashboardWindow} dashboardWindow
   * @param {string} apiUrl - Python backend URL
   */
  constructor(mainWindow, dashboardWindow, apiUrl) {
    this._mainWindow = mainWindow;
    this._dashboardWindow = dashboardWindow;
    this._apiUrl = apiUrl || 'http://127.0.0.1:8199';
    this._registered = [];
  }

  register() {
    // Ctrl+Shift+H: 显示/隐藏悬浮条
    const toggleSuccess = globalShortcut.register('CommandOrControl+Shift+H', () => {
      if (this._mainWindow.isVisible()) {
        this._mainWindow.hide();
      } else {
        this._mainWindow.show();
      }
    });

    if (toggleSuccess) {
      this._registered.push('CommandOrControl+Shift+H');
      console.log('Registered shortcut: Ctrl+Shift+H');
    }

    // Ctrl+Shift+D: 打开详情面板
    const dashboardSuccess = globalShortcut.register('CommandOrControl+Shift+D', () => {
      this._dashboardWindow.open(this._mainWindow);
    });

    if (dashboardSuccess) {
      this._registered.push('CommandOrControl+Shift+D');
      console.log('Registered shortcut: Ctrl+Shift+D');
    }

    // v3.0 Ctrl+Shift+C: 捕获当前选中内容到拾遗
    const captureSuccess = globalShortcut.register('CommandOrControl+Shift+C', async () => {
      await this._captureSelection();
    });

    if (captureSuccess) {
      this._registered.push('CommandOrControl+Shift+C');
      console.log('Registered shortcut: Ctrl+Shift+C (capture)');
    }

    // v3.0 Ctrl+Shift+Z: 切换主窗口显示/隐藏
    const togglePanelSuccess = globalShortcut.register('CommandOrControl+Shift+Z', () => {
      if (this._mainWindow.isVisible()) {
        this._mainWindow.hide();
      } else {
        this._mainWindow.show();
        this._mainWindow.focus();
      }
    });

    if (togglePanelSuccess) {
      this._registered.push('CommandOrControl+Shift+Z');
      console.log('Registered shortcut: Ctrl+Shift+Z (toggle panel)');
    }
  }

  /**
   * 捕获当前选中内容：模拟 Ctrl+C → 读取剪贴板 → 发送到拾遗 → 恢复原剪贴板
   */
  async _captureSelection() {
    try {
      // 1. 保存当前剪贴板内容
      const original = this._readClipboard();

      // 2. 模拟 Ctrl+C 复制当前选中内容
      this._simulateCopy();

      // 3. 等待剪贴板更新
      await new Promise(r => setTimeout(r, 200));

      // 4. 读取新剪贴板内容
      const captured = this._readClipboard();

      // 5. 判断是否有新内容
      const hasNewContent = (
        (captured.text && captured.text !== original.text) ||
        (captured.hasImage && captured.imageData !== original.imageData)
      );

      if (hasNewContent) {
        // 6. 发送到拾遗
        if (captured.hasImage) {
          const tmpPath = path.join(app.getPath('temp'), `eleven-capture-${Date.now()}.png`);
          fs.writeFileSync(tmpPath, captured.imageBuffer);
          await this._importFiles([tmpPath], 'hotkey');
        } else if (captured.text) {
          await this._importText(captured.text, captured.html, 'hotkey');
        }
        console.log('Selection captured to 拾遗');
      }

      // 7. 恢复原剪贴板内容
      this._restoreClipboard(original);
    } catch (e) {
      console.error('Capture selection failed:', e.message);
    }
  }

  _readClipboard() {
    const text = clipboard.readText();
    const html = clipboard.readHTML();
    const image = clipboard.readImage();
    const hasImage = !image.isEmpty();
    return {
      text,
      html,
      hasImage,
      imageData: hasImage ? image.toDataURL() : null,
      imageBuffer: hasImage ? image.toPNG() : null,
    };
  }

  _restoreClipboard(content) {
    if (content.hasImage && content.imageBuffer) {
      clipboard.writeImage(nativeImage.createFromBuffer(content.imageBuffer));
    } else if (content.html) {
      clipboard.writeHTML(content.html);
    } else if (content.text) {
      clipboard.writeText(content.text);
    }
  }

  _simulateCopy() {
    try {
      execSync(
        'powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait(\'^c\')"',
        { windowsHide: true, timeout: 2000 }
      );
    } catch {
      // Ignore timeout errors
    }
  }

  async _importFiles(files, source) {
    try {
      const res = await fetch(`${this._apiUrl}/api/items/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files, source, project: 'default' }),
      });
      return await res.json();
    } catch (e) {
      console.error('importFiles failed:', e.message);
    }
  }

  async _importText(text, html, source) {
    try {
      const res = await fetch(`${this._apiUrl}/api/items/import-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content_text: text, content_html: html, source, project: 'default' }),
      });
      return await res.json();
    } catch (e) {
      console.error('importText failed:', e.message);
    }
  }

  unregisterAll() {
    globalShortcut.unregisterAll();
    this._registered = [];
    console.log('All shortcuts unregistered');
  }
}

module.exports = ShortcutManager;
