const { app, BrowserWindow, globalShortcut, Tray, Menu, ipcMain, Notification } = require('electron');
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

// Function to poll backend status for notifications
function pollStatusForNotification() {
    setInterval(async () => {
        try {
            const res = await axios.get('http://127.0.0.1:8000/status');
            if (res.data.status === 'ready' && !hasNotifiedReady) {
                new Notification({
                    title: 'AuraWhisper',
                    body: 'AI model loaded and system is ready!',
                    silent: false
                }).show();
                hasNotifiedReady = true;
            } else if (res.data.status === 'loading') {
                hasNotifiedReady = false; // Reset if it goes back to loading (e.g. model change)
            }
        } catch (e) {
            // Backend might not be up yet
        }
    }, 2000);
}


function startPythonBackend() {
    // Check if backend is already alive before spawning
    axios.get('http://127.0.0.1:8000/status')
        .then(() => {
            console.log('Backend is already running. Skipping spawn.');
            pollStatusForNotification();
        })
        .catch(() => {
            const pythonExe = path.join(__dirname, 'backend', 'venv', 'Scripts', 'python.exe');
            const scriptPath = path.join(__dirname, 'backend', 'server.py');
            
            console.log(`Starting backend with: ${pythonExe}`);
            
            pythonProcess = spawn(pythonExe, [scriptPath], {
                cwd: path.join(__dirname, 'backend')
            });

            pythonProcess.stdout.on('data', (data) => {
                console.log(`Py stdout: ${data}`);
            });

            pythonProcess.stderr.on('data', (data) => {
                console.error(`Py stderr: ${data}`);
            });

            pythonProcess.on('close', (code) => {
                console.log(`Backend process exited with code ${code}`);
                pythonProcess = null;
            });
        });
}



function stopPythonBackend() {
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
    mainWindow = new BrowserWindow({
        width: 400,
        height: 150,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        focusable: false, // Prevent the window from taking focus away from other apps
        show: false,
        webPreferences: {

            nodeIntegration: true,
            contextIsolation: false
        }
    });

    mainWindow.loadFile('ui/index.html');
}

function createSettingsWindow() {
    if (settingsWindow) {
        settingsWindow.focus();
        return;
    }

    settingsWindow = new BrowserWindow({
        width: 450,
        height: 650,
        minWidth: 400,
        minHeight: 500,
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

    settingsWindow.loadFile('ui/settings.html');

    settingsWindow.on('closed', () => {
        settingsWindow = null;
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
    const config = loadConfig();
    globalShortcut.unregisterAll();

    if (config.mode === 'hold') {
        console.log('Hold mode active: Global shortcut managed by backend.');
        return;
    }

    let hotkey = config.hotkey || 'Alt+Shift+U';
    
    // Normalize hotkey string to ensure consistency (Alt+Shift+U format)
    hotkey = hotkey.split('+').map(part => {
        const p = part.trim().toLowerCase();
        return p.charAt(0).toUpperCase() + p.slice(1);
    }).join('+').replace('Ctrl', 'CommandOrControl');

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
    } else {
        console.log(`SUCCESS: Global hotkey [${hotkey}] is now ACTIVE.`);
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

    ipcMain.on('config-updated', () => {
        console.log('Config updated signal received.');
        registerHotkey();
        axios.post('http://127.0.0.1:8000/config/reload').catch(e => console.error(e));
    });

    // Tray Icon
    try {
        tray = new Tray(path.join(__dirname, 'ui/icon.png')); 
        const contextMenu = Menu.buildFromTemplate([
            { label: 'Settings', click: () => createSettingsWindow() },
            { label: 'Show Recorder', click: () => {
                if (!mainWindow) createWindow();
                mainWindow.show();
            }},
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
