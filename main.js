const { app, BrowserWindow, globalShortcut, Tray, Menu, ipcMain, Notification, shell } = require('electron');

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
            axios.get('http://127.0.0.1:8000/config'),
            axios.get('http://127.0.0.1:8000/modes')
        ]);
        const config = cRes.data;
        const modes = mRes.data;

        const menu = Menu.buildFromTemplate(modes.map(m => ({
            label: m.name,
            type: 'radio',
            checked: m.id === config.active_mode_id,
            click: async () => {
                config.active_mode_id = m.id;
                await axios.post('http://127.0.0.1:8000/config', config);
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
            axios.get('http://127.0.0.1:8000/config'),
            axios.get('http://127.0.0.1:8000/history'),
            axios.get('http://127.0.0.1:8000/modes')
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
                        await axios.post('http://127.0.0.1:8000/reprocess_last');
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
                            await axios.post('http://127.0.0.1:8000/paste', { text: h.text });
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
                    config.use_ollama = item.checked;
                    await axios.post('http://127.0.0.1:8000/config', config);
                }
            },
            {
                label: 'Auto Punctuation',
                type: 'checkbox',
                checked: config.auto_punctuation,
                click: async (item) => {
                    config.auto_punctuation = item.checked;
                    await axios.post('http://127.0.0.1:8000/config', config);
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
            await axios.post('http://127.0.0.1:8000/config', config);
            if (mainWindow) mainWindow.webContents.send('config-updated');
        }
        async function updateStyle(s) {
            config.window_style = s;
            await axios.post('http://127.0.0.1:8000/config', config);
            if (mainWindow) mainWindow.webContents.send('config-updated');
        }

        menu.popup(BrowserWindow.fromWebContents(event.sender));
    } catch (err) {
        console.error('Failed to show context menu:', err.message);
    }
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
function pollStatusForNotification() {
    if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
    }
    
    console.log('Starting backend status polling...');
    pollingTimer = setInterval(async () => {
        try {
            const res = await axios.get('http://127.0.0.1:8000/status', { timeout: 3000 });
            consecutiveFailures = 0; // Reset on success

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
                // If process is still running, it might just be extremely slow or loading a huge model
                if (pythonProcess && consecutiveFailures < FAILURE_THRESHOLD * 2) {
                    console.log('Backend is non-responsive but process is still ALIVE. Waiting longer...');
                    return; 
                }

                console.error('Backend lost connection or failed to start. Attempting auto-restart...');
                consecutiveFailures = 0;
                hasNotifiedReady = false;
                
                // Stop and restart
                stopPythonBackend();
                setTimeout(() => {
                    startPythonBackend();
                    new Notification({
                        title: 'AuraWhisper Recovery',
                        body: 'Attempting to recover backend service...',
                        silent: false
                    }).show();
                }, 2000);
            }
        }
    }, 2000);
}


function startPythonBackend() {
    // Check if backend is already alive before spawning
    axios.get('http://127.0.0.1:8000/status', { timeout: 2000 })
        .then(() => {
            console.log('Backend is already running. Skipping spawn.');
            pollStatusForNotification();
        })
        .catch(() => {
            let pythonExe;
            let scriptPath;
            let cwd;

            if (app.isPackaged) {
                // When packaged, app files are in resources/app
                cwd = path.join(process.resourcesPath, 'app', 'backend');
                pythonExe = path.join(cwd, 'venv', 'Scripts', 'python.exe');
                scriptPath = path.join(cwd, 'server.py');
            } else {
                cwd = path.join(__dirname, 'backend');
                pythonExe = path.join(cwd, 'venv', 'Scripts', 'python.exe');
                scriptPath = path.join(cwd, 'server.py');
            }

            // Fallback to system python if venv is missing (though venv is recommended)
            if (!fs.existsSync(pythonExe)) {
                pythonExe = 'python'; 
                console.log('[INFO] venv not found. Falling back to system python.');
            }

            console.log(`[DEBUG] Attempting to spawn backend:`);
            console.log(`[DEBUG] Python Path: ${pythonExe}`);
            console.log(`[DEBUG] Script Path: ${scriptPath}`);
            console.log(`[DEBUG] Working Dir: ${cwd}`);

            pythonProcess = spawn(pythonExe, [scriptPath], {
                cwd: cwd,
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            pythonProcess.stdout.on('data', (data) => {
                console.log(`Py stdout: ${data}`);
            });

            pythonProcess.stderr.on('data', (data) => {
                console.error(`Py stderr: ${data}`);
            });

            pythonProcess.on('error', (err) => {
                console.error(`[ERROR] Failed to start backend process: ${err.message}`);
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
    if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
    }
    consecutiveFailures = 0;

    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
}

// Check if we started in settings-only mode
const isSettingsMode = process.argv.includes('--settings');

const CONFIG_PATH = path.join(__dirname, 'config.json');

function loadConfig() {
    try {
        const data = fs.readFileSync(CONFIG_PATH, 'utf-8');
        return JSON.parse(data);
    } catch (e) {
        return { hotkey: 'Alt+Shift+S', mode: 'toggle' };
    }
}

function createWindow() {
    const config = loadConfig();
    mainWindow = new BrowserWindow({
        width: config.window_style === 'mini' ? 320 : 450,
        height: config.window_style === 'mini' ? 120 : 200,
        x: config.window_x,
        y: config.window_y,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: true, // Required for dragging in some cases
        focusable: false,
        show: false,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
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
            contextIsolation: false
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

        // Use Alt+Shift+S as fallback if hotkey is missing or empty
        let hotkey = config.hotkey || 'Alt+Shift+S';
        
        // Final fallback if empty string was passed
        if (hotkey.trim() === '') hotkey = 'Alt+Shift+S';

        // Normalize hotkey string to ensure consistency (Alt+Shift+U format)
        hotkey = hotkey.split('+').map(part => {
            const p = part.trim().toLowerCase();
            if (!p) return '';
            return p.charAt(0).toUpperCase() + p.slice(1);
        }).filter(p => p !== '').join('+').replace('Ctrl', 'CommandOrControl');

        console.log(`Attempting to register global hotkey: [${hotkey}]`);

        const ret = globalShortcut.register(hotkey, async () => {
            console.log(`Hotkey pressed: [${hotkey}]`);
            if (!isRecording) {
                try {
                    console.log('Sending start recording request to backend...');
                    await axios.post('http://127.0.0.1:8000/start');
                    isRecording = true;
                    if (mainWindow) mainWindow.showInactive();
                } catch (err) {
                    console.error('Error starting recording:', err.message);
                    showWindow();
                }
            } else {
                try {
                    console.log('Sending stop recording request to backend...');
                    await axios.post('http://127.0.0.1:8000/stop');
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
            // Try default as last resort
            if (hotkey !== 'Alt+Shift+S') {
                console.log('Attempting to register default Alt+Shift+S...');
                globalShortcut.register('Alt+Shift+S', () => { /* same logic or call registerHotkey with force default */ });
            }
        } else {
            console.log(`SUCCESS: Global hotkey [${hotkey}] is now ACTIVE.`);
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
            const currentSize = mainWindow.getSize();
            if (currentSize[0] !== width || currentSize[1] !== height) {
                mainWindow.setSize(width, height, true);
            }
        }
    });


    ipcMain.on('config-updated', () => {
        console.log('Config updated signal received.');
        registerHotkey();
        axios.post('http://127.0.0.1:8000/config/reload').catch(e => console.error(e));
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
            { label: 'Settings', click: () => createSettingsWindow() },
            {
                label: 'Show Recorder', click: () => {
                    if (!mainWindow) createWindow();
                    mainWindow.show();
                }
            },
            { type: 'separator' },
            { label: 'Quit', click: () => app.quit() }
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
