import { app, BrowserWindow, shell, dialog, ipcMain, Menu } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { join } from 'path';
import { spawn, ChildProcess } from 'child_process';
import { existsSync, chmodSync, appendFileSync } from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Logging function for debugging packaged apps
const logToFile = (message: string) => {
  if (app.isPackaged) {
    const logPath = join(app.getPath('userData'), 'mcp-brag.log');
    const timestamp = new Date().toISOString();
    try {
      appendFileSync(logPath, `[${timestamp}] ${message}\n`);
    } catch (error) {
      console.error('Failed to write to log file:', error);
    }
  }
  console.log(message);
};

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (process.platform === 'win32') {
  require('electron-squirrel-startup');
}

let mainWindow: BrowserWindow | null = null;
let pythonServer: ChildProcess | null = null;

const startPythonServer = () => {
  let pythonPath: string;
  let pyzPath: string;

  if (!process.env.USE_SERVER_BINARY && !app.isPackaged) {
    logToFile('Not using server binary, server must be run independently/manually');
    return;
  }
  logToFile('Starting BRAG [MCP] server...');

  // Use the Python executable with .pyz script
  if (app.isPackaged) {
    // In packaged app, the Python and pyz are in the resources directory
    pythonPath = join(process.resourcesPath, 'python');
    pyzPath = join(process.resourcesPath, 'mcp_server.pyz');
    logToFile(`Packaged app - Python: ${pythonPath}, PYZ: ${pyzPath}`);
  } else {
    // In development, use the Python and pyz from server-dist
    pythonPath = join(__dirname, '../../server-dist/python');
    pyzPath = join(__dirname, '../../server-dist/mcp_server.pyz');
    logToFile(`Development mode - Python: ${pythonPath}, PYZ: ${pyzPath}`);
  }

  // Check if the Python executable and pyz script exist
  if (!existsSync(pythonPath)) {
    logToFile(`ERROR: Python executable not found at: ${pythonPath}`);
    dialog.showErrorBox(
      'Server Error',
      `Python executable not found at:\n${pythonPath}\n\nPlease ensure the server is built and packaged correctly.`
    );
    return;
  }

  if (!existsSync(pyzPath)) {
    logToFile(`ERROR: PYZ script not found at: ${pyzPath}`);
    dialog.showErrorBox(
      'Server Error',
      `MCP Server PYZ script not found at:\n${pyzPath}\n\nPlease ensure the server is built and packaged correctly.`
    );
    return;
  }

  // Ensure the Python executable is executable (important for macOS)
  try {
    if (process.platform !== 'win32') {
      logToFile('Setting executable permissions for Python binary...');
      chmodSync(pythonPath, 0o755);
    }
  } catch (error) {
    logToFile(`ERROR: Failed to set executable permissions: ${error}`);
  }

  logToFile('Spawning server process...');

  // Spawn with explicit environment variables
  const env = { ...process.env };

  try {
    pythonServer = spawn(pythonPath, [pyzPath], {
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: false,
    });

    logToFile(`Server process started with PID: ${pythonServer.pid}`);

    pythonServer.stdout?.on('data', (data) => {
      logToFile(`[MCP Server stdout]: ${data.toString().trim()}`);
    });

    pythonServer.stderr?.on('data', (data) => {
      logToFile(`[MCP Server stderr]: ${data.toString().trim()}`);
    });

    pythonServer.on('error', (error) => {
      logToFile(`ERROR: Failed to start server process: ${error}`);
      dialog.showErrorBox('Server Error', `Failed to start MCP Server:\n${error.message}`);
    });

    pythonServer.on('close', (code, signal) => {
      logToFile(`Python server process exited with code ${code} and signal ${signal}`);
      pythonServer = null;

      if (app.isPackaged && code !== 0) {
        // only restart in packaged app if it crashed
        logToFile('Server crashed. Restarting in 5 seconds...');
        setTimeout(startPythonServer, 5000);
      }
    });

    // Give the server time to start and check if it's running
    setTimeout(() => {
      if (pythonServer && !pythonServer.killed) {
        logToFile('Server appears to be running. Checking health...');
        // You could add a health check here
        checkServerHealth();
      }
    }, 2000);
  } catch (error) {
    logToFile(`ERROR: Exception while starting server: ${error}`);
    dialog.showErrorBox('Server Error', `Exception starting MCP Server:\n${error}`);
  }
};

// Add a function to check if the server is responding
const checkServerHealth = async () => {
  try {
    const response = await fetch('http://localhost:8000/health');
    if (response.ok) {
      logToFile('Server health check passed');
    } else {
      logToFile(`WARNING: Server health check failed with status: ${response.status}`);
    }
  } catch (error) {
    logToFile(`WARNING: Server health check failed: ${error}`);
  }
};

async function createWindow() {
  // Create the browser window.
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'BRAG [MCP]',
    webPreferences: {
      preload: app.isPackaged
        ? path.join(process.resourcesPath, 'app.asar', '.vite', 'build', 'preload.js')
        : path.join(__dirname, '../../.vite/preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
      allowRunningInsecureContent: true,
    },
    icon: path.join(__dirname, '../../src/images/icon.png'),
  });

  // Load the app
  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/main_window/index.html'));
  }

  // Open external links in the browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Open devtools in development
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  // Test actively push message to the Electron-Renderer
  mainWindow.webContents.send('main-process-message', new Date().toLocaleString());

  // Create application menu with debug options
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: 'BRAG [MCP]',
      submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'quit' }],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Debug',
      submenu: [
        {
          label: 'Show Log File',
          click: () => {
            const logPath = join(app.getPath('userData'), 'mcp-brag.log');
            shell.showItemInFolder(logPath);
          },
        },
        {
          label: 'Show Server Status',
          click: () => {
            const status = {
              serverRunning: pythonServer !== null && !pythonServer.killed,
              serverPID: pythonServer?.pid,
              resourcesPath: process.resourcesPath,
              isPackaged: app.isPackaged,
              pythonPath: app.isPackaged
                ? join(process.resourcesPath, 'python')
                : join(__dirname, '../../server-dist/python'),
              pyzPath: app.isPackaged
                ? join(process.resourcesPath, 'mcp_server.pyz')
                : join(__dirname, '../../server-dist/mcp_server.pyz'),
            };
            dialog.showMessageBox(mainWindow!, {
              type: 'info',
              title: 'Server Status',
              message: 'MCP Server Status',
              detail: JSON.stringify(status, null, 2),
              buttons: ['OK'],
            });
          },
        },
        { type: 'separator' },
        {
          label: 'Restart Server',
          click: () => {
            if (pythonServer) {
              pythonServer.kill();
            }
            setTimeout(startPythonServer, 1000);
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// This method will be called when Electron has finished initialization
app.whenReady().then(() => {
  // Set up IPC handlers
  ipcMain.handle('select-file-or-directory', async (): Promise<string | null> => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openFile', 'openDirectory'],
      title: 'Select a file or directory to process',
    });

    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0];
    }
    return null;
  });

  // Configure session to allow localhost connections
  // const ses = session.defaultSession;

  // Remove any CORS or header modifications as they are no longer needed with webSecurity disabled
  // Previously, we had code here to handle CORS headers, but it's now removed

  ipcMain.on('ping', () => console.log('pong'));

  // Add handler to check server status
  ipcMain.handle('get-server-status', () => {
    return {
      running: pythonServer !== null && !pythonServer.killed,
      pid: pythonServer?.pid,
      resourcesPath: process.resourcesPath,
      isPackaged: app.isPackaged,
    };
  });

  // Add handler to restart the entire application
  ipcMain.handle('restart-app', () => {
    logToFile('App restart requested via IPC');
    app.relaunch();
    app.quit();
  });

  startPythonServer();
  createWindow();

  app.on('activate', () => {
    // On macOS, re-create a window when the dock icon is clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    // Someone tried to run a second instance, focus our window instead
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

app.on('will-quit', () => {
  if (pythonServer) {
    console.log('Terminating Python server...');
    pythonServer.kill();
  }
});
