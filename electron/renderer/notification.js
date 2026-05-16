/**
 * 通知模块
 * 气泡通知：滑入/淡出动画
 */

class NotificationManager {
  constructor() {
    this._container = document.getElementById('notificationContainer');
    this._queue = [];
    this._isShowing = false;
  }

  show(message, duration = 3000) {
    this._queue.push({ message, duration });
    if (!this._isShowing) {
      this._showNext();
    }
  }

  _showNext() {
    if (this._queue.length === 0) {
      this._isShowing = false;
      return;
    }

    this._isShowing = true;
    const { message, duration } = this._queue.shift();

    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;

    // 添加到容器
    if (this._container) {
      this._container.appendChild(notification);

      // 自动消失
      setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
          notification.remove();
          this._showNext();
        }, 300);
      }, duration);
    }
  }
}

// 导出到全局
window.NotificationManager = new NotificationManager();

// 监听主进程通知
window.electronAPI.showNotification &&
  window.electronAPI.onShowNotification?.((message) => {
    window.NotificationManager.show(message);
  });
