const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // 窗口控制
  moveWindow: (deltaX, deltaY) => ipcRenderer.send('window-move', { deltaX, deltaY }),
  getWindowBounds: () => ipcRenderer.invoke('get-window-bounds'),
  toggleVisibility: () => ipcRenderer.send('toggle-visibility'),
  openDashboard: () => ipcRenderer.send('open-dashboard'),

  // 数据监听
  onDataUpdate: (callback) => ipcRenderer.on('data-update', (event, data) => callback(data)),
  onStateChange: (callback) => ipcRenderer.on('state-change', (event, state) => callback(state)),
  onNewItem: (callback) => ipcRenderer.on('new-item', (event, data) => callback(data)),

  // 剪贴板操作
  getItems: (limit, cursor) => ipcRenderer.invoke('get-items', { limit, cursor }),
  searchItems: (query) => ipcRenderer.invoke('search-items', query),
  copyItem: (id) => ipcRenderer.invoke('copy-item', id),
  deleteItem: (id) => ipcRenderer.invoke('delete-item', id),
  pinItem: (id) => ipcRenderer.invoke('pin-item', id),
  clearItems: () => ipcRenderer.invoke('clear-items'),

  // v3.0 中转站模式
  importFiles: (files, source) => ipcRenderer.invoke('import-files', { files, source }),

  // v3.0 项目空间
  getProjects: () => ipcRenderer.invoke('get-projects'),
  createProject: (name, icon, color) => ipcRenderer.invoke('create-project', { name, icon, color }),
  deleteProject: (id) => ipcRenderer.invoke('delete-project', id),

  // 通知
  showNotification: (message) => ipcRenderer.send('show-notification', message)
});
