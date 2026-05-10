const { app, BrowserWindow, globalShortcut, Tray, Menu, ipcMain, Notification, shell, screen } = require('electron');

const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
    process.exit(0);
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();
        }
    });
}

// Disable hardware acceleration to fix transparency issues on some Windows systems
app.disableHardwareAcceleration();

if (process.platform === 'win32') {
    app.commandLine.appendSwitch('enable-transparent-visuals');
}

// ... (中略)

ipcMain.on('relaunch-app', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
    app.relaunch();
    app.exit(0);
});

ipcMain.on('show-mode-menu', async (event) => {
    try {
        const [cRes, mRes] = await Promise.all([
            axios.get('http://127.0.0.1:8240/config'),
            axios.get('http://127.0.0.1:8240/modes')
        ]);
        const config = cRes.data;
        const modes = mRes.data;

        const menu = Menu.buildFromTemplate(modes.map(m => ({
            label: m.name,
            type: 'radio',
            checked: m.id === config.active_mode_id,
            click: async () => {
                await axios.post('http://127.0.0.1:8240/config', { active_mode_id: m.id });
                if (mainWindow) mainWindow.webContents.send('mode-updated', m);
            }
        })));
        
        menu.popup(BrowserWindow.fromWebContents(event.sender));
    } catch (err) {
        console.error('Failed to show mode menu:', err.message);
    }
});

ipcMain.on('show-context-menu', async (event) => {
    try {
        const [cRes, hRes, mRes] = await Promise.all([
            axios.get('http://127.0.0.1:8240/config'),
            axios.get('http://127.0.0.1:8240/history'),
            axios.get('http://127.0.0.1:8240/modes')
        ]);
        const config = cRes.data;
        const history = hRes.data.slice(0, 5);
        const modes = mRes.data;
        const activeMode = modes.find(m => m.id === config.active_mode_id);

        const menu = Menu.buildFromTemplate([
            {
                label: `Re-process Last (${activeMode ? activeMode.name : 'Current Mode'})`,
                click: async () => {
                    try {
                        await axios.post('http://127.0.0.1:8240/reprocess_last');
                    } catch (e) {
                        console.error('Reprocess failed:', e);
                    }
                }
            },
            { type: 'separator' },
            {
                label: 'Recent History',
                submenu: history.length > 0 ? history.map(h => ({
                    label: h.text.length > 30 ? h.text.substring(0, 30) + '...' : h.text,
                    click: async () => {
                        try {
                            await axios.post('http://127.0.0.1:8240/paste', { text: h.text });
                        } catch (e) {
                            console.error('Quick paste failed:', e);
                        }
                    }
                })) : [{ label: 'No history', enabled: false }]
            },
            { type: 'separator' },
            {
                label: 'AI Refinement',
                type: 'checkbox',
                checked: config.use_ollama,
                click: async (item) => {
                    await axios.post('http://127.0.0.1:8240/config', { use_ollama: item.checked });
                }
            },
            {
                label: 'Auto Punctuation',
                type: 'checkbox',
                checked: config.auto_punctuation,
                click: async (item) => {
                    await axios.post('http://127.0.0.1:8240/config', { auto_punctuation: item.checked });
                }
            },
            { type: 'separator' },
            {
                label: 'Language',
                submenu: [
                    { label: 'Japanese', type: 'radio', checked: config.language === 'ja', click: () => updateLang('ja') },
                    { label: 'English', type: 'radio', checked: config.language === 'en', click: () => updateLang('en') },
                    { label: 'Auto', type: 'radio', checked: config.language === 'auto', click: () => updateLang('auto') }
                ]
            },
            {
                label: 'Window Style',
                submenu: [
                    { label: 'Classic', type: 'radio', checked: config.window_style === 'classic', click: () => updateStyle('classic') },
                    { label: 'Mini', type: 'radio', checked: config.window_style === 'mini', click: () => updateStyle('mini') }
                ]
            },
            { type: 'separator' },
            { label: 'Settings...', click: () => createSettingsWindow() },
            { label: 'Quit', click: () => app.quit() }
        ]);

        async function updateLang(l) {
            config.language = l;
            await axios.post('http://127.0.0.1:8240/config', config);
            if (mainWindow) mainWindow.webContents.send('config-updated');
        }
        async function updateStyle(s) {
            config.window_style = s;
            await axios.post('http://127.0.0.1:8240/config', config);
            if (mainWindow) mainWindow.webContents.send('config-updated');
        }

        menu.popup(BrowserWindow.fromWebContents(event.sender));
    } catch (err) {
        console.error('Failed to show context menu:', err.message);
    }
});

ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) win.setIgnoreMouseEvents(ignore, options || {});
});

const { spawn } = require('child_process');
const path = require('path');
const axios = require('axios');
const fs = require('fs');

let mainWindow;
let settingsWindow;
let tray;
let isRecording = false;
let pythonProcess = null;
let hasNotifiedReady = false;
let consecutiveFailures = 0;
let restartCount = 0;
let pollingTimer = null;
const MAX_RESTARTS = 5;
const FAILURE_THRESHOLD = 20; // 20 * 2s = 40s

// Function to poll backend status for notifications
let isPollingActive = false;
function pollStatusForNotification() {
    if (isPollingActive) return;
    isPollingActive = true;
    
    console.log('Starting backend status polling (recursive)...');
    
    async function checkStatus() {
        if (!isPollingActive) return;

        try {
            const res = await axios.get('http://127.0.0.1:8240/status', { timeout: 4000 });
            consecutiveFailures = 0;

            if (res.data.status === 'ready' && !hasNotifiedReady) {
                const config = loadConfig();
                if (config.notifications !== false) {
                    new Notification({
                        title: 'AuraWhisper',
                        body: 'AI Engine is ready!',
                        silent: true
                    }).show();
                }
                hasNotifiedReady = true;
            } else if (res.data.status === 'loading') {
                hasNotifiedReady = false;
            }
        } catch (e) {
            consecutiveFailures++;
            const errorType = e.code || e.message;
            console.log(`Backend offline... (${consecutiveFailures}/${FAILURE_THRESHOLD}) - Reason: ${errorType}`);
            
            if (consecutiveFailures >= FAILURE_THRESHOLD) {
                const fs = require('fs');
                let venvPython;
                if (app.isPackaged) {
                    const rootDir = path.dirname(app.getPath('exe'));
                    venvPython = path.join(rootDir, 'backend', 'venv', 'Scripts', 'python.exe');
                } else {
                    venvPython = path.join(__dirname, 'backend', 'venv', 'Scripts', 'python.exe');
                }
                
                if (!fs.existsSync(venvPython)) {
                    console.log('Virtual environment not found. Skipping recovery.');
                    consecutiveFailures = 0;
                } else if (pythonProcess && consecutiveFailures < 60) { // 60 * 2s = 120s
                    console.log('Backend is non-responsive but process is still ALIVE. Being patient...');
                } else {
                    console.error('Backend recovery triggered.');
                    consecutiveFailures = 0;
                    hasNotifiedReady = false;
                    
                    stopPythonBackend();
                    setTimeout(() => {
                        startPythonBackend();
                        new Notification({
                            title: 'AuraWhisper Recovery',
                            body: 'Service is restarting to ensure stability...',
                            silent: false
                        }).show();
                    }, 2000);
                    return; // Stop this recursion, the new start will spin up a new one
                }
            }
        }
        
        if (isPollingActive) {
            setTimeout(checkStatus, 2000);
        }
    }
    
    checkStatus();
}


function startPythonBackend() {
    // Check if backend is already alive before spawning
    axios.get('http://127.0.0.1:8240/status', { timeout: 2000 })
        .then(() => {
            console.log('Backend is already running. Skipping spawn.');
            pollStatusForNotification();
        })
        .catch(() => {
            let pythonExe;
            let scriptPath;
            let cwd;

            // Use __dirname for simple, reliable path resolution in development and NSIS installation
            cwd = path.join(__dirname, 'backend');
            pythonExe = path.join(cwd, 'venv', 'Scripts', 'python.exe');
            scriptPath = path.join(cwd, 'server.py');

            // Fallback for portable layouts where backend is directly in app.getPath('exe') parent directory
            if (!fs.existsSync(pythonExe)) {
                const portableDir = path.join(path.dirname(app.getPath('exe')), 'backend');
                const portablePython = path.join(portableDir, 'venv', 'Scripts', 'python.exe');
                if (fs.existsSync(portablePython)) {
                    cwd = portableDir;
                    pythonExe = portablePython;
                    scriptPath = path.join(cwd, 'server.py');
                }
            }

            // Fallback to system python if venv is missing
            if (!fs.existsSync(pythonExe)) {
                pythonExe = 'python'; 
                console.log('[INFO] venv not found. Falling back to system python.');
            }

            // Final check: if neither venv nor system python works, alert user
            try {
                const { execSync } = require('child_process');
                execSync(`${pythonExe} --version`);
            } catch (e) {
                const { dialog } = require('electron');
                dialog.showErrorBox(
                    'Python Not Found',
                    'AuraWhisper requires Python to run.\n\nPlease install Python from python.org and ensure "Add to PATH" is checked during installation.'
                );
                return;
            }

            console.log(`Spawning backend: ${pythonExe} ${scriptPath}`);
            
            const debugLogPath = path.join(app.getPath('userData'), 'backend_debug.log');
            fs.writeFileSync(debugLogPath, `Backend start attempt: ${new Date().toLocaleString()}\n`);

            pythonProcess = spawn(pythonExe, [scriptPath], {
                cwd: cwd,
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            pythonProcess.stdout.on('data', (data) => {
                const msg = data.toString();
                fs.appendFileSync(debugLogPath, `[STDOUT] ${msg}`);
            });

            pythonProcess.stderr.on('data', (data) => {
                const msg = data.toString();
                fs.appendFileSync(debugLogPath, `[STDERR] ${msg}`);
            });

            pythonProcess.on('error', (err) => {
                const msg = `[${new Date().toISOString()}] SPAWN ERROR: ${err.message}\n`;
                console.error(msg);
                fs.appendFileSync(debugLogPath, msg);
            });

            pythonProcess.on('close', (code) => {
                console.log(`Backend process exited with code ${code}`);
                pythonProcess = null;
                
                if (code !== 0 && code !== null && restartCount < MAX_RESTARTS) {
                    restartCount++;
                    console.log(`Attempting auto-restart (${restartCount}/${MAX_RESTARTS})...`);
                    setTimeout(startPythonBackend, 3000);
                }
            });
            
            pollStatusForNotification();
        });
}



function stopPythonBackend() {
    isPollingActive = false;
    consecutiveFailures = 0;

    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
}

// Check if we started in settings-only mode
const isSettingsMode = process.argv.includes('--settings');

const CONFIG_PATH = path.join(app.getPath('userData'), 'config.json');

function loadConfig() {
    try {
        if (!fs.existsSync(CONFIG_PATH)) {
            const defaultPath = path.join(__dirname, 'config.json');
            if (fs.existsSync(defaultPath)) {
                fs.copyFileSync(defaultPath, CONFIG_PATH);
            } else {
                const defaultConfig = { hotkey: 'Alt+Shift+S', mode: 'toggle', language: 'ja', model_size: 'small', device: 'auto', use_ollama: false, ai_provider: 'lmstudio', ollama_base_url: 'http://localhost:1234/v1' };
                fs.writeFileSync(CONFIG_PATH, JSON.stringify(defaultConfig, null, 4), 'utf-8');
            }
        }
        const data = fs.readFileSync(CONFIG_PATH, 'utf-8');
        return JSON.parse(data);
    } catch (e) {
        return { hotkey: 'Alt+Shift+S', mode: 'toggle' };
    }
}

function createWindow() {
    const config = loadConfig();
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
    
    console.log(`[INFO] Detected Screen Resolution: ${screenWidth}x${screenHeight}`);

    const winWidth = config.window_style === 'mini' ? 320 : 450;
    const winHeight = config.window_style === 'mini' ? 350 : 500;

    // Use saved coordinates or default to center
    let x = config.window_x;
    let y = config.window_y;

    // If coordinates are missing or completely invalid, center it
    if (x === undefined || y === undefined) {
        x = Math.floor((screenWidth - winWidth) / 2);
        y = Math.floor((screenHeight - winHeight) / 2);
    } else {
        // Safety: Clamp coordinates to be within the current screen boundaries
        // This ensures the window is visible even if the user changed resolution or disconnected a monitor
        x = Math.max(0, Math.min(x, screenWidth - winWidth));
        y = Math.max(0, Math.min(y, screenHeight - winHeight));
    }

    console.log(`[INFO] Positioning window at: x=${x}, y=${y}`);

    mainWindow = new BrowserWindow({
        width: winWidth,
        height: winHeight,
        x: x,
        y: y,
        frame: false,
        transparent: true, // Re-enable transparency for v1.0.5
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: true,
        focusable: false,
        show: false,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            webSecurity: false
        }
    });

    // Save position when moved
    mainWindow.on('move', () => {
        const [x, y] = mainWindow.getPosition();
        const currentConfig = loadConfig();
        currentConfig.window_x = x;
        currentConfig.window_y = y;
        fs.writeFileSync(CONFIG_PATH, JSON.stringify(currentConfig, null, 4));
    });

    mainWindow.setMenu(null);
    mainWindow.loadFile('ui/index.html');
}

function createSettingsWindow() {
    if (settingsWindow) {
        settingsWindow.focus();
        return;
    }

    settingsWindow = new BrowserWindow({
        width: 1000,
        height: 750,
        minWidth: 900,
        minHeight: 650,
        title: 'AuraWhisper Settings',
        backgroundColor: '#0a0a0f',
        resizable: true,
        alwaysOnTop: true, // Ensure it's above the recorder
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            webSecurity: false
        }
    });

    // Optional: center relative to screen or main window
    if (mainWindow && !mainWindow.isDestroyed()) {
        const bounds = mainWindow.getBounds();
        settingsWindow.setPosition(bounds.x, bounds.y - 100); // Near the recorder but slightly above
        settingsWindow.center();
    }

    settingsWindow.setMenu(null);
    settingsWindow.loadFile('ui/settings.html');

    settingsWindow.on('closed', () => {
        settingsWindow = null;
        // Notify main window to refresh after settings close
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('config-updated');
        }
        // If we're in settings mode and no other windows are open, quit
        if (isSettingsMode && !mainWindow) {
            app.quit();
        }
    });
}

ipcMain.on('open-settings', () => {
    createSettingsWindow();
});

ipcMain.handle('get-local-config', () => {
    return loadConfig();
});

ipcMain.handle('save-local-config', (event, newConfig) => {
    try {
        const mergedConfig = { ...loadConfig(), ...newConfig };
        fs.writeFileSync(CONFIG_PATH, JSON.stringify(mergedConfig, null, 2), 'utf-8');
        return { success: true };
    } catch (e) {
        return { success: false, error: e.message };
    }
});

function showWindow() {
    if (mainWindow) {
        mainWindow.show();
    }
}

function registerHotkey() {
    try {
        const config = loadConfig();
        globalShortcut.unregisterAll();

        if (config.mode === 'hold') {
            console.log('Hold mode active: Global shortcut managed by backend.');
            return;
        }

        // Fallback
        let hotkey = config.hotkey || 'Alt+Shift+S';
        if (hotkey.trim() === '') hotkey = 'Alt+Shift+S';

        // Ensure proper Electron format
        hotkey = hotkey.replace('Control', 'CommandOrControl').replace('Ctrl', 'CommandOrControl');

        console.log(`Attempting to register global hotkey: [${hotkey}]`);

        const ret = globalShortcut.register(hotkey, async () => {
            console.log(`Hotkey pressed: [${hotkey}]`);
            if (!isRecording) {
                try {
                    console.log('Sending start recording request to backend...');
                    await axios.post('http://127.0.0.1:8240/start');
                    isRecording = true;
                    
                    if (!mainWindow || mainWindow.isDestroyed()) {
                        createWindow();
                    }
                    
                    if (mainWindow) {
                        mainWindow.setAlwaysOnTop(true, 'screen-saver');
                        mainWindow.show();
                        // Optional: Ensure it's not minimized
                        if (mainWindow.isMinimized()) mainWindow.restore();
                    }
                } catch (err) {
                    console.error('Error starting recording:', err.message);
                    if (!mainWindow || mainWindow.isDestroyed()) createWindow();
                    if (mainWindow) mainWindow.show();
                }
            } else {
                try {
                    console.log('Sending stop recording request to backend...');
                    await axios.post('http://127.0.0.1:8240/stop');
                    if (mainWindow) mainWindow.hide();
                    isRecording = false;
                } catch (err) {
                    console.error('Error stopping recording:', err.message);
                    isRecording = false;
                }
            }
        });

        if (!ret) {
            console.error(`CRITICAL ERROR: Hotkey registration failed for [${hotkey}]. It might be used by another application.`);
            const { dialog } = require('electron');
            dialog.showMessageBox({
                type: 'error',
                title: 'Shortcut Conflict',
                message: `Failed to register global hotkey: ${hotkey}`,
                detail: 'The shortcut is already being used by another application (like Snipping Tool or another recorder).\n\nPlease try changing the hotkey in the AuraWhisper settings.',
                buttons: ['OK']
            });
        }
    } catch (e) {
        console.error('Error in registerHotkey:', e.message);
    }
}


app.whenReady().then(() => {
    startPythonBackend();
    if (isSettingsMode) {
        createSettingsWindow();
        registerHotkey();
    } else {
        createWindow();
        registerHotkey();
    }

    pollStatusForNotification();


    ipcMain.on('open-settings', () => {
        createSettingsWindow();
    });

    ipcMain.on('resize-window', (event, { width, height }) => {
        if (mainWindow && !mainWindow.isDestroyed()) {
            const bounds = mainWindow.getBounds();
            if (bounds.width !== width || bounds.height !== height) {
                // Shift the y position to anchor movement from the bottom up
                const dy = height - bounds.height;
                mainWindow.setBounds({
                    x: bounds.x,
                    y: bounds.y - dy,
                    width: width,
                    height: height
                }, true);
            }
        }
    });


    ipcMain.on('config-updated', () => {
        console.log('Config updated signal received.');
        // Notify backend to reload config as well
        axios.post('http://127.0.0.1:8240/config/reload').catch(e => console.error('Failed to notify backend:', e.message));
        registerHotkey();
    });

    ipcMain.on('set-autostart', (event, enable) => {
        app.setLoginItemSettings({
            openAtLogin: enable,
            path: app.getPath('exe')
        });
        console.log(`Autostart ${enable ? 'enabled' : 'disabled'}`);
    });

    // Tray Icon
    try {
        tray = new Tray(path.join(__dirname, 'ui/icon.png'));
        const contextMenu = Menu.buildFromTemplate([
            {
                label: 'About AuraWhisper...', click: () => {
                    const { dialog } = require('electron');
                    dialog.showMessageBox({
                        type: 'info',
                        title: 'About AuraWhisper',
                        message: 'AuraWhisper v1.2.6',
                        detail: 'Premium dictation tool for Windows\n\nVersion: 1.2.6\nPlatform: ' + process.platform + ' (x64)',
                        buttons: ['OK']
                    });
                }
            },
            { type: 'separator' },
            { label: 'Settings', click: () => createSettingsWindow() },
            {
                label: 'Show Recorder', click: () => {
                    if (!mainWindow) createWindow();
                    mainWindow.show();
                }
            },
            {
                label: 'Reset Window Position', click: () => {
                    if (mainWindow && !mainWindow.isDestroyed()) {
                        const primaryDisplay = screen.getPrimaryDisplay();
                        const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
                        const winWidth = mainWindow.getSize()[0];
                        const winHeight = mainWindow.getSize()[1];
                        const cx = Math.floor((screenWidth - winWidth) / 2);
                        const cy = Math.floor((screenHeight - winHeight) / 2);
                        mainWindow.setPosition(cx, cy);
                        mainWindow.show();
                        
                        const currentConfig = loadConfig();
                        currentConfig.window_x = cx;
                        currentConfig.window_y = cy;
                        fs.writeFileSync(CONFIG_PATH, JSON.stringify(currentConfig, null, 4));
                    } else {
                        createWindow();
                        if (mainWindow) mainWindow.show();
                    }
                }
            },
            { type: 'separator' },
            {
                label: 'Check Backend Status', click: async () => {
                    try {
                        const res = await axios.get('http://127.0.0.1:8240/status', { timeout: 2000 });
                        new Notification({
                            title: 'AuraWhisper Status',
                            body: `Backend is running! Status: ${res.data.status}`,
                            silent: false
                        }).show();
                    } catch (e) {
                        new Notification({
                            title: 'AuraWhisper Status',
                            body: `Backend seems offline. Error: ${e.message}`,
                            silent: false
                        }).show();
                    }
                }
            },
            {
                label: 'Restart Backend', click: () => {
                    stopPythonBackend();
                    setTimeout(() => {
                        startPythonBackend();
                        new Notification({
                            title: 'AuraWhisper Status',
                            body: 'Restarting Backend Server...',
                            silent: false
                        }).show();
                    }, 1000);
                }
            },
            { type: 'separator' },
            { 
                label: 'Force Quit & Close All', click: () => {
                    stopPythonBackend();
                    app.quit();
                } 
            }
        ]);
        tray.setToolTip('AuraWhisper');
        tray.setContextMenu(contextMenu);
    } catch (e) {
        console.error("Tray icon failed to load:", e.message);
    }
});

// Avoid quitting when the recorder window is hidden
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin' && !isSettingsMode) {
        // Keep running in tray
    } else if (isSettingsMode && !mainWindow) {
        app.quit();
    }
});

app.on('will-quit', () => {
    stopPythonBackend();
});

ipcMain.on('start-engine-setup', (event, type) => {
    console.log(`Starting engine setup via IPC (type: ${type})`);
    
    const { exec } = require('child_process');
    const fs = require('fs');
    const path = require('path');

    let appRoot = __dirname;
    if (appRoot.endsWith('app') || appRoot.endsWith('app.asar')) {
        appRoot = path.dirname(appRoot);
    }
    const backendDir = path.join(__dirname, 'backend');
    
    event.reply('setup-progress', { percent: 10, status: 'Checking Python installation...' });
    
    exec('python --version', (err, stdout, stderr) => {
        if (err) {
            console.error('Global Python not found:', err);
            event.reply('setup-error', 'Global Python is not found on your system. Please install Python to continue.');
            return;
        }

        event.reply('setup-progress', { percent: 20, status: 'Creating Python virtual environment...' });

        try {
            if (fs.existsSync(path.join(backendDir, 'venv'))) {
                fs.rmSync(path.join(backendDir, 'venv'), { recursive: true, force: true });
            }
        } catch (e) {
            console.error('Failed to clean old venv:', e);
        }

        exec(`python -m venv "${path.join(backendDir, 'venv')}"`, (err, stdout, stderr) => {
            if (err) {
                console.error('Failed to create venv:', err);
                event.reply('setup-error', 'Failed to create venv: ' + err.message);
                return;
            }

            event.reply('setup-progress', { percent: 40, status: 'Upgrading pip in venv...' });

            const venvPython = path.join(backendDir, 'venv', 'Scripts', 'python.exe');

            exec(`"${venvPython}" -m pip install --upgrade pip`, (err, stdout, stderr) => {
                event.reply('setup-progress', { percent: 50, status: 'Installing base libraries (faster-whisper, fastapi)...' });

                let reqFile = path.join(backendDir, 'requirements.txt');
                if (!fs.existsSync(reqFile)) {
                    reqFile = path.join(backendDir, 'requirements-base.txt');
                }

                const installCmd = fs.existsSync(reqFile) 
                    ? `"${venvPython}" -m pip install --ignore-installed -r "${reqFile}"`
                    : `"${venvPython}" -m pip install --ignore-installed faster-whisper fastapi uvicorn pynput pyperclip pydantic httpx ctypes-callable sounddevice numpy scipy`;

                exec(installCmd, (err, stdout, stderr) => {
                    if (err) {
                        console.error('Failed to install base dependencies:', err);
                        event.reply('setup-error', 'Failed to install base dependencies: ' + err.message);
                        return;
                    }

                    if (type === 'gpu') {
                        event.reply('setup-progress', { percent: 70, status: 'Installing GPU libraries (CUDA)...' });
                        exec(`"${venvPython}" -m pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121`, (err, stdout, stderr) => {
                            event.reply('setup-progress', { percent: 90, status: 'Finalizing installation...' });
                            event.reply('setup-complete');
                        });
                    } else {
                        event.reply('setup-progress', { percent: 90, status: 'Finalizing installation...' });
                        event.reply('setup-complete');
                    }
                });
            });
        });
    });
});

ipcMain.on('relaunch-app', () => {
    try {
        const { globalShortcut } = require('electron');
        globalShortcut.unregisterAll();
    } catch (e) {
        console.error('Failed to unregister shortcuts during relaunch:', e);
    }
    app.relaunch();
    app.exit(0);
});
