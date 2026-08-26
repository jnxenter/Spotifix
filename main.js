const { app, BrowserWindow, Menu, Tray, ipcMain } = require('electron');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const axios = require('axios');
const treeKill = require('tree-kill');

const iconPath = path.join(__dirname, 'assets/icon.ico');
const isPackaged = app.isPackaged;
const appPath = isPackaged ? path.join(process.resourcesPath, 'app') : __dirname;

let mainWindow;
let splashScreen;
let loginWindow;
let backendProcess;
let tray = null;
let consoleShown = false;
let consoleWindow = null;

let aiServerProcess = null;
let aiServerPort = 47254;
let aiServerPass = '';
let aiSessionId = null;
const AI_MODEL = 'big-pickle';

const LOGIN_USER = 'SpotifixAPP';
const LOGIN_PASS = 'Melona2019.';

function authStateFile() {
    return path.join(app.getPath('userData'), 'authed.json');
}

function isAuthenticated() {
    try {
        return fs.existsSync(authStateFile());
    } catch (e) {
        return false;
    }
}

function markAuthenticated() {
    try {
        fs.writeFileSync(authStateFile(), JSON.stringify({ authed: true }));
    } catch (e) {
        console.error('Failed to save auth state:', e);
    }
}


app.disableHardwareAcceleration();
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', (event, commandLine, workingDirectory) => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.focus();
        }
    });


    function killProcessOnPort(port) {
        // Find the PID of the process using the specified port
        exec(`netstat -ano | findstr :${port}`, (err, stdout, stderr) => {
          if (err) {
            console.error(`Error finding process on port ${port}:`, stderr);
            return;
          }
      
          // Extract the PID from the command output
          const lines = stdout.trim().split('\n');
          if (lines.length > 0) {
            const parts = lines[0].trim().split(/\s+/);
            const pid = parts[parts.length - 1];
      
            // Kill the process with the found PID
            exec(`taskkill /PID ${pid} /F`, { windowsHide: true }, (err, stdout, stderr) => {
              if (err) {
                console.error(`Error killing process with PID ${pid}:`, stderr);
              } else {
                console.log(`Process with PID ${pid} on port ${port} was killed.`);
              }
            });
          } else {
            console.log(`No process found on port ${port}`);
          }
        });
      }




    app.on('window-all-closed', () => {
        if (process.platform !== 'darwin') {
            cleanUpAndQuit();
        }
    });

    

    function createSplashScreen() {
        splashScreen = new BrowserWindow({
            width: 300,
            height: 180,
            transparent: true,
            frame: false,
            alwaysOnTop: false,
            resizable: false,
            fullscreenable: false,
            icon: iconPath,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
                sandbox: true, // Enable sandboxing
            },
        });

        splashScreen.loadFile('splash.html');
        splashScreen.show();
        splashScreen.on('closed', () => {
            splashScreen = null;
        });
    }

    function createMainWindow(token) {
        if (splashScreen) {
            splashScreen.close(); // Close splash screen if main window is to be shown
        }

        Menu.setApplicationMenu(null);
        mainWindow = new BrowserWindow({
            minWidth: 1380,
            minHeight: 770,
            width: 1380,
            height: 770,
            resizable: true,
            frame: false,
            webPreferences: {
                preload: path.join(__dirname, 'preload.js'),
                nodeIntegration: false, // Disable Node.js integration
                contextIsolation: true, // Enforce context isolation
                enableRemoteModule: false, // Disable remote module for security
                sandbox: true, // Enable sandboxing for additional security
            },
        });

        mainWindow.loadFile('index.html').catch(err => {
            console.error('Failed to load index.html:', err);
        });
        mainWindow.webContents.on('did-finish-load', () => {
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('token-received', token);
            }
        });

        mainWindow.on('closed', () => {
            mainWindow = null;
            cleanUpAndQuit();
        });

        //if (process.env.NODE_ENV !== 'development') {
        //    mainWindow.webContents.on('devtools-opened', () => {
        //        mainWindow.webContents.closeDevTools();
        //    });
        //}
        //mainWindow.webContents.openDevTools();
    }

    async function autoLogin() {
        try {
            const response = await axios.post('http://127.0.0.1:8999/register', { username: 'local' });
            if (response.data.success) {
                return response.data.token;
            }
        } catch (error) {
            console.error('Auto-login failed:', error);
        }
        return '';
    }

    function createLoginWindow() {
        loginWindow = new BrowserWindow({
            width: 350,
            height: 522,
            resizable: false,
            frame: false,
            transparent: true,
            icon: iconPath,
            webPreferences: {
                preload: path.join(__dirname, 'preload.js'),
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
            },
        });

        loginWindow.loadFile('login.html');
        loginWindow.show();

        loginWindow.on('closed', () => {
            loginWindow = null;
        });
    }

    ipcMain.on('login-attempt', (event, data) => {
        const { payload } = data;
        const username = payload.username;
        const password = payload.password;

        if (username === LOGIN_USER && password === LOGIN_PASS) {
            markAuthenticated();
            event.reply('login-response', {
                success: true,
                message: 'Login successful!'
            });
        } else {
            event.reply('login-response', {
                success: false,
                message: 'Invalid credentials'
            });
        }
    });

    function createConsoleWindow() {
        consoleWindow = new BrowserWindow({
            width: 750,
            height: 470,
            minWidth: 750,
            minHeight: 470,
            frame: false,
            show: false, // Fenster zunächst versteckt
            icon: iconPath,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,  // empfohlen, um Sicherheitsprobleme zu vermeiden
                preload: path.join(__dirname, 'preload.js'),
                scrollable: false,
            },
        });

        consoleWindow.loadFile('console.html');
        consoleWindow.setMenu(null);

        consoleWindow.on('close', (event) => {
            if (!app.isQuitting) {
                event.preventDefault();
                consoleWindow.hide();
                consoleShown = false;
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.webContents.send('console-toggled', 'Show Console');
                }
            } else {
                consoleWindow = null; // If app is quitting, allow window to close properly
            }
        });

        consoleWindow.on('closed', () => {
            consoleWindow = null;
        });

        consoleWindow.on('show', () => {
            consoleShown = true;
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('console-toggled', 'Hide Console');
            }
        });

        consoleWindow.on('hide', () => {
            consoleShown = false;
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('console-toggled', 'Show Console');
            }
        });
    }


    async function waitForBackendReady() {
        while (true) {
            try {
                console.log('Attempting to check backend readiness...');
                const response = await axios.post('http://127.0.0.1:8999/backend');
                if (response.data.ready) {
                    console.log('Backend is ready');
                    break;
                } else {
                    console.log(`Backend not ready yet, reason: ${response.data.message}. Retrying in 1 second...`);
                }
            } catch (error) {
                console.log(`Error checking backend readiness: ${error.message}. Retrying in 1 second...`);
            }
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    ipcMain.on('toggle-console', (event) => {
        if (consoleWindow === null) {
            createConsoleWindow();
        }

        if (consoleWindow.isVisible()) {
            consoleWindow.hide();
        } else {
            consoleWindow.show();
        }
    });

    ipcMain.on('close-app', () => {
        const focusedWindow = BrowserWindow.getFocusedWindow();
        if (focusedWindow) {
            focusedWindow.close();
        }
    });

    app.on('before-quit', () => {
        console.log('Application is quitting. Terminating backend process...');
        app.isQuitting = true;  // Set a flag indicating app is quitting
        cleanUpAndQuit();
    });

    ipcMain.on('minimize-app', () => {
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.minimize();
    });

    ipcMain.on('close-window', () => {
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.close();
    });

    function createTray() {
        tray = new Tray(iconPath);
        const contextMenu = Menu.buildFromTemplate([
            {
                label: 'Show',
                click: () => {
                    if (mainWindow) {
                        mainWindow.show();
                    }
                }
            },
            {
                label: 'Exit',
                click: () => {
                    cleanUpAndQuit();
                }
            }
        ]);

        tray.setToolTip(`Spotifix`);
        tray.setContextMenu(contextMenu);
    }

    function spawnBackend() {
        const apiExePath = path.join(appPath, 'api.exe');
        const apiExePathAlt = path.join(appPath, 'api', 'api.exe');
        const apiPyPath = path.join(appPath, 'api.py');
        let proc;
        if (fs.existsSync(apiExePath)) {
            proc = spawn(apiExePath, [], { cwd: appPath });
        } else if (fs.existsSync(apiExePathAlt)) {
            proc = spawn(apiExePathAlt, [], { cwd: path.join(appPath, 'api') });
        } else if (fs.existsSync(apiPyPath)) {
            proc = spawn('python', [apiPyPath], { cwd: appPath });
        } else {
            proc = spawn('python', ['api.py']); // fallback
        }

        proc.stdout.on('data', (data) => {
            console.log(`[Backend] ${data}`);
        });

        proc.stderr.on('data', (data) => {
            console.error(`[Backend] ${data}`);
        });

        proc.on('error', (err) => {
            console.error('Backend process error:', err);
        });

        proc.on('exit', (code, signal) => {
            console.log(`Backend process exited with code ${code} signal ${signal}`);
            backendProcess = null;
            const restartFlag = path.join(appPath, '_update_restart');
            let isUpdateRestart = false;
            try {
                if (fs.existsSync(restartFlag)) {
                    isUpdateRestart = true;
                    fs.unlinkSync(restartFlag);
                }
            } catch (e) {}
            if (isUpdateRestart) {
                console.log('Update restart detected. Relaunching app...');
                setTimeout(() => {
                    app.relaunch({ args: process.argv.slice(1) });
                    app.exit(0);
                }, 500);
                return;
            }
            if (!app.isQuitting) {
                console.log('Restarting backend in 3 seconds...');
                setTimeout(() => {
                    if (!app.isQuitting) {
                        backendProcess = spawnBackend();
                    }
                }, 3000);
            }
        });

        return proc;
    }

    let backendHealthInterval = null;

    function startBackendHealthCheck() {
        // Check backend health every 30 seconds
        backendHealthInterval = setInterval(async () => {
            try {
                const response = await axios.post('http://127.0.0.1:8999/backend');
                if (!response.data.ready) {
                    console.log('Backend health check: not ready yet');
                }
            } catch (error) {
                console.error('Backend health check failed:', error.message);
                // Backend is down; if process is null, restart will happen via exit handler
                if (!backendProcess || backendProcess.killed) {
                    console.log('Backend process is dead, health check will rely on exit handler');
                }
            }
        }, 30000);
    }

    // ---------------- IA (openCode) ----------------

    function aiAuthHeader() {
        return 'Basic ' + Buffer.from('opencode:' + aiServerPass).toString('base64');
    }

    function resolveOpenCodeBin() {
        const candidates = [];
        if (process.env.OPENCODE_BIN) candidates.push(process.env.OPENCODE_BIN);
        candidates.push(path.join(appPath, 'opencode.exe'));
        candidates.push(path.join(appPath, 'resources', 'opencode.exe'));
        if (process.env.APPDATA) {
            candidates.push(path.join(process.env.APPDATA, 'npm', 'node_modules', 'opencode-ai', 'bin', 'opencode.exe'));
        }
        for (const c of candidates) {
            try {
                if (fs.existsSync(c)) return c;
            } catch (e) {}
        }
        return 'opencode';
    }

    function aiDataDir() {
        return path.join(app.getPath('userData'), 'opencode-data');
    }

    function spawnAIServer() {
        if (aiServerProcess && !aiServerProcess.killed) return aiServerProcess;
        aiServerPass = crypto.randomUUID();
        const bin = resolveOpenCodeBin();
        const args = ['serve', '--port', String(aiServerPort), '--hostname', '127.0.0.1'];
        console.log(`[AI] spawning ${bin} on port ${aiServerPort}`);
        try { require('fs').writeFileSync(process.env.TEMP + '\\opencode\\ai_pass.txt', aiServerPass); } catch (e) {}
        aiServerProcess = spawn(bin, args, {
            cwd: appPath,
            windowsHide: true,
            env: Object.assign({}, process.env, {
                OPENCODE_SERVER_USERNAME: 'opencode',
                OPENCODE_SERVER_PASSWORD: aiServerPass,
                XDG_DATA_HOME: aiDataDir(),
            }),
        });
        aiServerProcess.stdout.on('data', (d) => { console.log(`[AI] ${d}`); });
        aiServerProcess.stderr.on('data', (d) => { console.error(`[AI] ${d}`); });
        aiServerProcess.on('error', (err) => { console.error('[AI] spawn error:', err); });
        aiServerProcess.on('exit', (code, signal) => {
            console.log(`[AI] server exited code ${code} signal ${signal}`);
            aiServerProcess = null;
            aiSessionId = null;
        });
        return aiServerProcess;
    }

    async function waitForAIServer(timeoutMs) {
        const deadline = Date.now() + (timeoutMs || 30000);
        while (Date.now() < deadline) {
            try {
                const res = await axios.get(`http://127.0.0.1:${aiServerPort}/global/health`, {
                    headers: { Authorization: aiAuthHeader() },
                    timeout: 3000,
                });
                if (res.data && res.data.healthy) return true;
            } catch (e) {}
            await new Promise((r) => setTimeout(r, 500));
        }
        return false;
    }

    async function aiPost(url, data, timeoutMs) {
        const res = await axios.post(`http://127.0.0.1:${aiServerPort}${url}`, data, {
            headers: { 'Content-Type': 'application/json', Authorization: aiAuthHeader() },
            timeout: timeoutMs || 30000,
        });
        return res.data;
    }

    async function aiGet(url, timeoutMs) {
        const res = await axios.get(`http://127.0.0.1:${aiServerPort}${url}`, {
            headers: { Authorization: aiAuthHeader() },
            timeout: timeoutMs || 15000,
        });
        return res.data;
    }

    function aiSleep(ms) {
        return new Promise((r) => setTimeout(r, ms));
    }

    function aiPermissionRules() {
        return {
            permission: [
                { permission: 'bash', pattern: '*', action: 'allow' },
                { permission: 'read', pattern: '*', action: 'allow' },
                { permission: 'edit', pattern: '*', action: 'allow' },
                { permission: 'write', pattern: '*', action: 'allow' },
                { permission: 'glob', pattern: '*', action: 'allow' },
                { permission: 'grep', pattern: '*', action: 'allow' },
                { permission: 'webfetch', pattern: '*', action: 'allow' },
                { permission: 'websearch', pattern: '*', action: 'allow' },
                { permission: 'task', pattern: '*', action: 'allow' },
                { permission: 'skill', pattern: '*', action: 'allow' },
                { permission: 'external_directory', pattern: '*', action: 'allow' },
                { permission: 'doom_loop', pattern: '*', action: 'allow' },
                { permission: 'question', pattern: '*', action: 'deny' },
            ],
        };
    }

    async function aiEnsureSession() {
        if (aiSessionId) return aiSessionId;
        const res = await aiPost('/session', Object.assign({ title: 'Spotifix IA' }, aiPermissionRules()), 60000);
        aiSessionId = res.id;
        return aiSessionId;
    }

    async function aiChatText(text, onProgress) {
        let sid = await aiEnsureSession();
        try {
            await aiPost(`/session/${sid}/prompt_async`, {
                parts: [{ type: 'text', text }],
                model: { providerID: 'opencode', modelID: AI_MODEL },
            }, 120000);
        } catch (err) {
            if (err.response && err.response.status === 404) {
                aiSessionId = null;
                sid = await aiEnsureSession();
                await aiPost(`/session/${sid}/prompt_async`, {
                    parts: [{ type: 'text', text }],
                    model: { providerID: 'opencode', modelID: AI_MODEL },
                }, 120000);
            } else {
                throw err;
            }
        }

        const deadline = Date.now() + (6 * 60 * 60 * 1000);
        let lastText = '';
        while (Date.now() < deadline) {
            if (!aiServerProcess || aiServerProcess.killed) {
                throw new Error('El servidor de IA se detuvo durante la tarea');
            }
            await aiSleep(1500);
            let data;
            try {
                data = await aiGet(`/session/${sid}/message?limit=2`, 30000);
            } catch (e) { continue; }
            if (!Array.isArray(data) || !data.length) continue;
            const last = data[data.length - 1];
            const parts = (last && last.parts) || [];
            const textParts = parts
                .filter((p) => p.type === 'text' && typeof p.text === 'string')
                .map((p) => p.text);
            const full = textParts.join('\n').trim();
            if (full && full !== lastText) {
                lastText = full;
                if (onProgress) onProgress(full);
            }
            const info = (last && last.info) || {};
            const done = info.done === true || (info.time && info.time.completed);
            if (done) {
                return { text: full || lastText, parts: parts };
            }
        }
        throw new Error('La tarea superó el tiempo máximo de espera (6 horas)');
    }

    ipcMain.handle('ai-status', async () => {
        if (!aiServerProcess || aiServerProcess.killed) {
            spawnAIServer();
        }
        const ready = await waitForAIServer(15000);
        return { ready, session: !!aiSessionId, port: aiServerPort, model: AI_MODEL };
    });

    ipcMain.handle('ai-chat', async (event, payload) => {
        const text = (payload && payload.text) || '';
        if (!text.trim()) return { ok: false, error: 'Mensaje vacío' };
        try {
            if (!aiServerProcess || aiServerProcess.killed) spawnAIServer();
            const ready = await waitForAIServer(60000);
            if (!ready) return { ok: false, error: 'El servidor de IA no pudo iniciarse' };
            const result = await aiChatText(text, (progress) => {
                if (event && event.sender && !event.sender.isDestroyed()) {
                    event.sender.send('ai-progress', progress);
                }
            });
            return { ok: true, text: result.text };
        } catch (err) {
            console.error('[AI] chat error:', err);
            let detail = err.message;
            if (err.response && err.response.data) {
                const d = err.response.data;
                detail = (d.data && d.data.message) || (typeof d === 'string' ? d : JSON.stringify(d));
            }
            return { ok: false, error: detail };
        }
    });

    ipcMain.handle('ai-reset', async () => {
        aiSessionId = null;
        return { ok: true };
    });

    app.on('ready', async () => {
        const restartFlag = path.join(appPath, '_update_restart');
        try { if (fs.existsSync(restartFlag)) fs.unlinkSync(restartFlag); } catch (e) {}
        killProcessOnPort(8999);
        backendProcess = spawnBackend();
        spawnAIServer();

        createSplashScreen();

        try {
            await waitForBackendReady();
            console.log('Backend is ready');
        } catch (error) {
            console.error('An error occurred:', error);
        }

        startBackendHealthCheck();
        if (isAuthenticated()) {
            proceedToMain();
        } else {
            createLoginWindow();
        }
    });

    async function proceedToMain() {
        const token = await autoLogin();
        if (loginWindow) {
            loginWindow.close();
        }
        createMainWindow(token);
        createTray();
    }

    ipcMain.on('login-success', (event) => {
        markAuthenticated();
        proceedToMain();
    });

    function cleanUpAndQuit() {
        console.log('Cleaning up before quitting...');
        if (aiServerProcess && !aiServerProcess.killed) {
            treeKill(aiServerProcess.pid, 'SIGTERM', () => {});
            aiServerProcess = null;
        }
        if (backendHealthInterval) {
            clearInterval(backendHealthInterval);
            backendHealthInterval = null;
        }
        if (backendProcess && !backendProcess.killed) {
            treeKill(backendProcess.pid, 'SIGTERM', (err) => {
                if (err) {
                    console.error('Failed to kill backend process:', err);
                } else {
                    console.log('Backend process terminated.');
                }
                backendProcess = null;
                app.quit();
            });
        } else {
            app.quit();
        }
    }
}

