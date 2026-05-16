/**
 * Gateway 数据采集层
 * HTTP 轮询 + WebSocket 实时推送
 */

const { BrowserWindow } = require('electron');

class GatewayMonitor {
  constructor(mainWindow, options = {}) {
    this._mainWindow = mainWindow;
    this._interval = options.interval || 5000;
    this._apiUrl = options.apiUrl || 'http://127.0.0.1:8199';
    this._timer = null;
    this._retryCount = 0;
    this._maxRetries = options.maxRetries || 3;
    this._ws = null;
    this._wsReconnectTimer = null;
    this._badgeCallback = null;
  }

  onBadgeUpdate(callback) {
    this._badgeCallback = callback;
  }

  start() {
    if (this._timer) return;

    // 立即采集一次
    this._fetch();

    // 定时采集
    this._timer = setInterval(() => this._fetch(), this._interval);

    // 建立 WebSocket 连接
    this._connectWebSocket();

    console.log(`Gateway monitor started, API: ${this._apiUrl}`);
  }

  stop() {
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = null;
    }
    if (this._wsReconnectTimer) {
      clearTimeout(this._wsReconnectTimer);
      this._wsReconnectTimer = null;
    }
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
  }

  async _fetch() {
    try {
      const res = await fetch(`${this._apiUrl}/api/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // 发送到渲染进程
      if (this._mainWindow && !this._mainWindow.isDestroyed()) {
        this._mainWindow.webContents.send('data-update', {
          status: data.status || 'online',
          count: data.count || 0,
          max_items: data.max_items || 200,
          storage_mode: data.storage_mode || 'volatile',
        });
      }

      this._retryCount = 0;
    } catch (error) {
      console.error('Gateway fetch error:', error.message);
      this._retryCount++;

      if (this._retryCount >= this._maxRetries) {
        this._sendState('offline');
      }
    }
  }

  _connectWebSocket() {
    const wsUrl = this._apiUrl.replace('http', 'ws') + '/ws';

    try {
      const WebSocket = require('ws');
      this._ws = new WebSocket(wsUrl);

      this._ws.on('open', () => {
        console.log('WebSocket connected');
        this._retryCount = 0;
      });

      this._ws.on('message', (data) => {
        try {
          const msg = JSON.parse(data.toString());
          if (msg.event === 'items-changed') {
            const count = msg.data.count || 0;
            // 实时推送剪贴板变化
            if (this._mainWindow && !this._mainWindow.isDestroyed()) {
              this._mainWindow.webContents.send('data-update', {
                status: 'online',
                count,
              });
              this._mainWindow.webContents.send('new-item', msg.data);
            }
            // 悬浮球角标更新
            if (this._badgeCallback) {
              this._badgeCallback(count);
            }
          }
        } catch (e) {
          // 忽略解析错误
        }
      });

      this._ws.on('close', () => {
        console.log('WebSocket disconnected, reconnecting in 3s...');
        this._ws = null;
        this._wsReconnectTimer = setTimeout(() => this._connectWebSocket(), 3000);
      });

      this._ws.on('error', (err) => {
        console.error('WebSocket error:', err.message);
      });
    } catch (e) {
      console.error('WebSocket not available, using HTTP polling only');
    }
  }

  _sendState(state) {
    if (this._mainWindow && !this._mainWindow.isDestroyed()) {
      this._mainWindow.webContents.send('state-change', state);
    }
  }
}

module.exports = GatewayMonitor;
