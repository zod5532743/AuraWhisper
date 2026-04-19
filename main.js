const { app, BrowserWindow, globalShortcut, Tray, Menu, ipcMain } = require('electron');
const path = require('path');
const axios = require('axios');
const fs = require('fs');

let mainWindow;
let settingsWindow;
let tray;
let isRecording = false;

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
        width: 400,
        height: 500,
        title: 'UltraWhisper Settings',
        backgroundColor: '#141419',
        resizable: false,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

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

    const hotkey = config.hotkey || 'Alt+Shift+S';
    const ret = globalShortcut.register(hotkey, async () => {
        if (!isRecording) {
            try {
                await axios.post('http://127.0.0.1:8000/start');
                isRecording = true;
                showWindow();
            } catch (err) {
                console.error('Error starting recording:', err.message);
                showWindow();
            }
        } else {
            try {
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
        console.error(`Error: Hotkey registration failed for [${hotkey}]`);
    } else {
        console.log(`Success: Registered global hotkey [${hotkey}]`);
    }
}

app.whenReady().then(() => {
    if (isSettingsMode) {
        createSettingsWindow();
        // We still register hotkey so the app is "active" in tray if started this way
        registerHotkey();
    } else {
        createWindow();
        registerHotkey();
    }

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
        tray.setToolTip('UltraWhisper');
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
