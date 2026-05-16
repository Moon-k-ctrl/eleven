/**
 * 拖拽移动 + 位置记忆模块
 * 使用 CSS -webkit-app-region: drag 实现基础拖拽
 * 通过 mousemove 事件计算精确位移
 */

class DragPosition {
  constructor() {
    this._isDragging = false;
    this._startX = 0;
    this._startY = 0;
    this._init();
  }

  _init() {
    const bar = document.getElementById('floatingBar');
    if (!bar) return;

    // 基础拖拽由 CSS -webkit-app-region: drag 处理
    // 这里添加精确的位置跟踪
    bar.addEventListener('mousedown', (e) => this._onMouseDown(e));
    document.addEventListener('mousemove', (e) => this._onMouseMove(e));
    document.addEventListener('mouseup', () => this._onMouseUp());
  }

  _onMouseDown(e) {
    this._isDragging = true;
    this._startX = e.screenX;
    this._startY = e.screenY;
  }

  async _onMouseMove(e) {
    if (!this._isDragging) return;

    const deltaX = e.screenX - this._startX;
    const deltaY = e.screenY - this._startY;

    // 只有移动超过阈值才触发窗口移动
    if (Math.abs(deltaX) > 1 || Math.abs(deltaY) > 1) {
      window.electronAPI.moveWindow(deltaX, deltaY);
      this._startX = e.screenX;
      this._startY = e.screenY;
    }
  }

  _onMouseUp() {
    if (!this._isDragging) return;
    this._isDragging = false;

    // 位置已保存，main.js 中的 'moved' 事件会自动保存
  }
}

// 初始化
new DragPosition();
