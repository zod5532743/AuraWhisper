// Minimal test to check if execSync works inside Electron
const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const cwd = path.join(__dirname, 'backend');
const pythonExe = path.join(cwd, 'venv', 'Scripts', 'python.exe');
const scriptPath = path.join(cwd, 'server.py');

// Write results to a file so we can read them later
const logFile = path.join(__dirname, 'electron_test_result.txt');

function log(msg) {
    console.log(msg);
    fs.appendFileSync(logFile, msg + '\n');
}

log('=== Electron execSync Test ===');
log('__dirname: ' + __dirname);
log('cwd: ' + cwd);
log('pythonExe: ' + pythonExe);
log('pythonExe exists: ' + fs.existsSync(pythonExe));
log('scriptPath exists: ' + fs.existsSync(scriptPath));

// Test import
log('\n--- Import Check ---');
try {
    execSync(`"${pythonExe}" -c "import fastapi, uvicorn, faster_whisper, sounddevice; print('OK')"`, { timeout: 30000 });
    log('IMPORT CHECK PASSED');
} catch (e) {
    log('IMPORT CHECK FAILED: ' + e.message);
    if (e.stderr) log('STDERR: ' + e.stderr.toString());
}

// Test spawn
log('\n--- Spawn Test ---');
const child = spawn(pythonExe, [scriptPath], {
    cwd: cwd,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
});

const stderrChunks = [];
child.stderr.on('data', (data) => { stderrChunks.push(data.toString()); });
child.stdout.on('data', (data) => { log('[STDOUT] ' + data.toString()); });
child.on('error', (err) => { log('SPAWN ERROR: ' + err.message); });
child.on('close', (code) => { log('Process closed with code: ' + code); process.exit(0); });

setTimeout(() => {
    log('Process still running after 5s - SUCCESS');
    log('STDERR (first 1000 chars): ' + stderrChunks.join('').substring(0, 1000));
    child.kill();
    process.exit(0);
}, 5000);
