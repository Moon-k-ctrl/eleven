const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const Store = require('electron-store');
const { spawn } = require('child_process');

// 导入主进程模块
const TrayManager = require('./main/tray');
const GatewayMonitor = require('./main/gateway-monitor');
const DashboardWindow = require('./main/dashboard-window');
const ShortcutManager = require('./main/shortcuts');
const FloatingBallWindow = require('./main/floating-ball');

const PYTHON_PORT = 8199;
const PYTHON_API = `http://127.0.0.1:${PYTHON_PORT}`;

const store = new Store();
let mainWindow = null;
let trayManager = null;
let gatewayMonitor = null;
let dashboardWindow = null;
let shortcutManager = null;
let floatingBall = null;
let pythonProcess = null;

// ── Python 子进程管理 ──

function startPythonBackend() {
  const isDev = !app.isPackaged;
  let cmd, args, opts;

  if (isDev) {
    // 开发模式：直接调用 python
    cmd = 'python';
    args = ['-m', 'src.server'];
    opts = { cwd: path.join(__dirname, '..'), stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true };
  } else {
    // 生产模式：调用打包后的 exe
    const exePath = path.join(process.resourcesPath, 'backend', 'eleven-backend.exe');
    cmd = exePath;
    args = [];
    opts = { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true };
  }

  console.log(`Starting backend: ${cmd} ${args.join(' ')}`);
  pythonProcess = spawn(cmd, args, opts);

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python] ${data.toString().trim()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
    pythonProcess = null;
  });

  pythonProcess.on('error', (err) => {
    console.error('Failed to start Python:', err.message);
    pythonProcess = null;
  });
}

async function waitForPython(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${PYTHON_API}/api/status`);
      if (res.ok) return true;
    } catch {
      // 还没启动，继续等待
    }
    await new Promise(r => setTimeout(r, 300));
  }
  return false;
}

function killPython() {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

// ── CLI 参数解析 + 文件导入 ──

function parseFileArgs(argv) {
  const files = [];
  let mode = null;
  for (let i = 1; i < argv.length; i++) {
    if (argv[i] === '--add' || argv[i] === '--add-multi') {
      mode = argv[i];
    } else if (mode && !argv[i].startsWith('--')) {
      if (fs.existsSync(argv[i])) {
        files.push(argv[i]);
      }
      mode = null;
    }
  }
  return files;
}

async function importFilesViaApi(filePaths, source = 'context-menu') {
  try {
    const res = await fetch(`${PYTHON_API}/api/items/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: filePaths, source, project: 'default' }),
    });
    return await res.json();
  } catch (e) {
    console.error('importFilesViaApi failed:', e.message);
    return { error: e.message };
  }
}

// Parse CLI args early (before single-instance check)
const cliFiles = parseFileArgs(process.argv);

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  // 读取上次位置或默认右上角
  const savedBounds = store.get('windowBounds', {
    x: width - 320,
    y: 20,
    width: 300,
    height: 40
  });

  mainWindow = new BrowserWindow({
    width: savedBounds.width,
    height: savedBounds.height,
    x: savedBounds.x,
    y: savedBounds.y,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile('index.html');

  // 窗口可穿透点击（仅拖拽区域响应）
  mainWindow.setIgnoreMouseEvents(false);

  // 保存位置
  mainWindow.on('moved', () => {
    if (mainWindow) {
      store.set('windowBounds', mainWindow.getBounds());
    }
  });

  // 初始化详情面板
  dashboardWindow = new DashboardWindow();

  // 初始化数据采集（连接 Python 后端）
  gatewayMonitor = new GatewayMonitor(mainWindow, { apiUrl: PYTHON_API });
  gatewayMonitor.start();

  // 初始化快捷键
  shortcutManager = new ShortcutManager(mainWindow, dashboardWindow, PYTHON_API);
  shortcutManager.register();

  // 初始化悬浮球（v3.0）
  floatingBall = new FloatingBallWindow({ store, apiUrl: PYTHON_API });
  floatingBall.create();

  // 连接角标更新
  if (gatewayMonitor) {
    gatewayMonitor.onBadgeUpdate((count) => {
      floatingBall?.updateBadge(count);
    });
  }

  // 初始化系统托盘（需要 floatingBall 引用）
  trayManager = new TrayManager(mainWindow, dashboardWindow, floatingBall);

  // 开发模式打开 DevTools
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

// IPC 处理
ipcMain.on('window-move', (event, { deltaX, deltaY }) => {
  if (mainWindow) {
    const [x, y] = mainWindow.getPosition();
    mainWindow.setPosition(x + deltaX, y + deltaY);
  }
});

ipcMain.handle('get-window-bounds', () => {
  return mainWindow ? mainWindow.getBounds() : null;
});

ipcMain.on('toggle-visibility', () => {
  if (mainWindow) {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
    }
  }
});

ipcMain.on('open-dashboard', () => {
  if (dashboardWindow) {
    dashboardWindow.open(mainWindow);
  }
});

// ── 剪贴板操作 IPC ──

ipcMain.handle('get-items', async (event, { limit = 50, cursor = null } = {}) => {
  try {
    const url = new URL(`${PYTHON_API}/api/items`);
    url.searchParams.set('limit', limit);
    if (cursor) url.searchParams.set('cursor', cursor);
    const res = await fetch(url);
    return await res.json();
  } catch (e) {
    return { items: [], has_more: false };
  }
});

ipcMain.handle('search-items', async (event, query) => {
  try {
    const res = await fetch(`${PYTHON_API}/api/items/search?q=${encodeURIComponent(query)}`);
    return await res.json();
  } catch (e) {
    return { items: [] };
  }
});

ipcMain.handle('copy-item', async (event, itemId) => {
  try {
    const res = await fetch(`${PYTHON_API}/api/items/${itemId}/copy`, { method: 'POST' });
    return await res.json();
  } catch (e) {
    return { error: e.message };
  }
});

ipcMain.handle('delete-item', async (event, itemId) => {
  try {
    const res = await fetch(`${PYTHON_API}/api/items/${itemId}`, { method: 'DELETE' });
    return await res.json();
  } catch (e) {
    return { error: e.message };
  }
});

ipcMain.handle('pin-item', async (event, itemId) => {
  try {
    const res = await fetch(`${PYTHON_API}/api/items/${itemId}/pin`, { method: 'POST' });
    return await res.json();
  } catch (e) {
    return { error: e.message };
  }
});

ipcMain.handle('clear-items', async () => {
  try {
    const res = await fetch(`${PYTHON_API}/api/items/clear`, { method: 'POST' });
    return await res.json();
  } catch (e) {
    return { error: e.message };
  }
});

// ── 文件导入 IPC（v3.0 中转站模式）──

ipcMain.handle('import-files', async (event, { files, source }) => {
  return importFilesViaApi(files, source || 'context-menu');
});

// ── 项目空间 IPC（v3.0）──

ipcMain.handle('get-projects', async () => {
  try {
    const res = await fetch(`${PYTHON_API}/api/projects`);
    return await res.json();
  } catch (e) {
    return { projects: [] };
  }
});

ipcMain.handle('create-project', async (event, { name, icon, color }) => {
  try {
    const res = await fetch(`${PYTHON_API}/api/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, icon: icon || '📁', color: color || '#4A90D9' }),
    });
    return await res.json();
  } catch (e) {
    return { error: e.message };
  }
});

ipcMain.handle('delete-project', async (event, projectId) => {
  try {
    const res = await fetch(`${PYTHON_API}/api/projects/${projectId}`, { method: 'DELETE' });
    return await res.json();
  } catch (e) {
    return { error: e.message };
  }
});

// ── 单实例锁（v3.0 右键菜单支持）──

const gotLock = app.requestSingleInstanceLock();

if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', (event, argv, workingDirectory) => {
    // 第二个实例传入的文件路径
    const newFiles = parseFileArgs(argv);
    if (newFiles.length > 0) {
      importFilesViaApi(newFiles, 'context-menu');
    }
    // 聚焦已有窗口
    if (mainWindow) {
      if (!mainWindow.isVisible()) mainWindow.show();
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    startPythonBackend();
    const ready = await waitForPython();
    if (!ready) {
      console.error('Python backend failed to start');
    }
    createWindow();

    // 命令行传入的文件（右键「发送到拾遗」）
    if (cliFiles.length > 0) {
      await importFilesViaApi(cliFiles, 'context-menu');
    }
  });
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// 清理资源
app.on('before-quit', () => {
  if (shortcutManager) {
    shortcutManager.unregisterAll();
  }
  if (floatingBall) {
    floatingBall.destroy();
  }
  if (gatewayMonitor) {
    gatewayMonitor.stop();
  }
  if (trayManager) {
    trayManager.destroy();
  }
  killPython();
});
