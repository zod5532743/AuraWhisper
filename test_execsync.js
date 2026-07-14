// main.js と同じ条件で execSync をテスト
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const cwd = path.join(__dirname, 'backend');
const pythonExe = path.join(cwd, 'venv', 'Scripts', 'python.exe');
const scriptPath = path.join(cwd, 'server.py');

console.log('cwd:', cwd);
console.log('pythonExe:', pythonExe);
console.log('pythonExe exists:', fs.existsSync(pythonExe));
console.log('scriptPath:', scriptPath);
console.log('scriptPath exists:', fs.existsSync(scriptPath));

// Test 1: Import check (same as main.js line 349)
console.log('\n--- Test 1: Import check ---');
try {
    execSync(`"${pythonExe}" -c "import fastapi, uvicorn, faster_whisper, sounddevice"`, { timeout: 30000 });
    console.log('IMPORT CHECK PASSED');
} catch (e) {
    console.log('IMPORT CHECK FAILED:', e.message);
}

// Test 2: Spawn equivalent
console.log('\n--- Test 2: spawn python server.py (wait 3s) ---');
const { spawn } = require('child_process');
const child = spawn(pythonExe, [scriptPath], {
    cwd: cwd,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
});

let stdoutData = '';
let stderrData = '';

child.stdout.on('data', (data) => { stdoutData += data.toString(); });
child.stderr.on('data', (data) => { stderrData += data.toString(); });

child.on('error', (err) => { console.log('SPAWN ERROR:', err.message); });

child.on('close', (code) => {
    console.log('Process closed with code:', code);
    console.log('STDOUT:', stdoutData.substring(0, 500));
    process.exit(0);
});

setTimeout(() => {
    console.log('Process still running after 5s - OK');
    console.log('STDERR (first 500 chars):', stderrData.substring(0, 500));
    child.kill();
    process.exit(0);
}, 5000);
