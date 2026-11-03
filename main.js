const { app, BrowserWindow, Menu, Tray, ipcMain, dialog } = require('electron');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const axios = require('axios');
const treeKill = require('tree-kill');
const { pipeline } = require('stream/promises');

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

function pendingSourceUpdateVersion() {
    // Las versiones antiguas actualizan main.js/preload.js desde GitHub y
    // crean esta marca antes de reiniciar. El nuevo main la convierte en una
    // actualización completa del instalador, sin pedir al usuario que baje un
    // archivo manualmente.
    try {
        const flag = path.join(appPath, '_update_restart');
        if (!fs.existsSync(flag)) return '';
        const version = fs.readFileSync(flag, 'utf8').trim();
        return /^v?\d+(?:\.\d+){1,3}$/.test(version) ? version.replace(/^v/, '') : '';
    } catch (e) {
        return '';
    }
}

function clearPendingSourceUpdate() {
    try { fs.unlinkSync(path.join(appPath, '_update_restart')); } catch (e) {}
}

async function launchVerifiedInstaller(version) {
    const tag = `v${String(version).replace(/^v/, '')}`;
    const releaseUrl = `https://api.github.com/repos/jnxenter/Spotifix/releases/tags/${tag}`;
    const releaseResponse = await axios.get(releaseUrl, {
        headers: { 'User-Agent': 'SonicPush-Installer-Updater', 'Accept': 'application/vnd.github+json' },
        timeout: 30000,
    });
    const assets = Array.isArray(releaseResponse.data.assets) ? releaseResponse.data.assets : [];
    const asset = assets.find(item => /\.exe$/i.test(String(item.name || '')));
    if (!asset || !asset.browser_download_url || !String(asset.digest || '').startsWith('sha256:')) {
        throw new Error(`La Release ${tag} aún no tiene un instalador verificable.`);
    }
    const updatesDir = path.join(app.getPath('temp'), 'SonicPush', 'updates');
    fs.mkdirSync(updatesDir, { recursive: true });
    const safeName = String(asset.name).replace(/[^A-Za-z0-9._ -]/g, '_');
    const installerPath = path.join(updatesDir, safeName);
    const partialPath = `${installerPath}.part`;
    const hash = crypto.createHash('sha256');
    const download = await axios.get(asset.browser_download_url, {
        responseType: 'stream', timeout: 0,
        headers: { 'User-Agent': 'SonicPush-Installer-Updater' },
    });
    download.data.on('data', chunk => hash.update(chunk));
    await pipeline(download.data, fs.createWriteStream(partialPath));
    const actual = hash.digest('hex').toLowerCase();
    const expected = String(asset.digest).split(':', 2)[1].toLowerCase();
    if (actual !== expected) {
        try { fs.unlinkSync(partialPath); } catch (e) {}
        throw new Error('La verificación SHA-256 del instalador falló.');
    }
    fs.renameSync(partialPath, installerPath);
    const launcherPath = path.join(updatesDir, `_install_${tag}.cmd`);
    const exeName = 'SonicPush STA.exe';
    fs.writeFileSync(launcherPath,
        '@echo off\r\n' +
        'timeout /t 3 /nobreak >nul\r\n' +
        `taskkill /f /im "${exeName}" >nul 2>&1\r\n` +
        `start "" /wait "${installerPath}" /S\r\n` +
        `if exist "${process.execPath}" start "" "${process.execPath}"\r\n` +
        'del /f /q "%~f0" >nul 2>&1\r\n',
        'ascii');
    require('child_process').spawn('cmd', ['/c', launcherPath], {
        detached: true, stdio: 'ignore', windowsHide: true,
    }).unref();
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

        Menu.setApplicationMenu(Menu.buildFromTemplate([
            { label: 'Edit', submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' },
                { role: 'selectAll' }
            ]}
        ]));
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

        mainWindow.webContents.on('context-menu', (event, params) => {
            const menu = Menu.buildFromTemplate([
                { label: 'Cortar', role: 'cut', enabled: params.selectionText.length > 0 },
                { label: 'Copiar', role: 'copy', enabled: params.selectionText.length > 0 },
                { label: 'Pegar', role: 'paste', enabled: params.isEditable },
                { type: 'separator' },
                { label: 'Seleccionar todo', role: 'selectAll', enabled: params.isEditable }
            ]);
            menu.popup();
        });
        mainWindow.webContents.on('did-finish-load', () => {
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('token-received', token);
            }
        });

        // Safety: re-send token until renderer confirms (avoids race where DOMContentLoaded
        // registers the token listener after did-finish-load already fired).
        let tokenRetries = 0;
        const tokenRetryInterval = setInterval(() => {
            if (!mainWindow || mainWindow.isDestroyed()) {
                clearInterval(tokenRetryInterval);
                return;
            }
            if (tokenRetries >= 10) {
                clearInterval(tokenRetryInterval);
                return;
            }
            tokenRetries += 1;
            mainWindow.webContents.send('token-received', token);
        }, 500);

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
        const startedAt = Date.now();
        let timeoutWarned = false;
        while (true) {
            try {
                console.log('Attempting to check backend readiness...');
                const response = await axios.post('http://127.0.0.1:8999/backend');
                if (response.data.ready) {
                    console.log('Backend is ready');
                    backendFastFailures = 0;
                    backendErrorDialogOpen = false;
                    break;
                } else {
                    console.log(`Backend not ready yet, reason: ${response.data.message}. Retrying in 1 second...`);
                }
            } catch (error) {
                console.log(`Error checking backend readiness: ${error.message}. Retrying in 1 second...`);
            }
            if (!timeoutWarned && Date.now() - startedAt > BACKEND_READY_TIMEOUT_MS) {
                timeoutWarned = true;
                showBackendErrorDialog('El backend lleva mas de 60 segundos sin responder.');
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

    ipcMain.on('restart-app', () => {
        console.log('Restart requested via IPC. Relaunching...');
        if (backendProcess && !backendProcess.killed) {
            treeKill(backendProcess.pid, 'SIGTERM', () => {});
        }
        setTimeout(() => {
            app.relaunch({ args: process.argv.slice(1) });
            app.exit(0);
        }, 1000);
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

        tray.setToolTip(`SonicPush STA`);
        tray.setContextMenu(contextMenu);
    }

    // ---- Diagnostico de arranque del backend ----
    // Si el backend muere al iniciar (dependencias faltantes, python ausente,
    // puerto ocupado, etc.) la app se quedaba en "Starting..." para siempre.
    // Guardamos la salida real y mostramos un dialogo con el error.
    let backendLogLines = [];
    let backendLastSpawnAt = 0;
    let backendFastFailures = 0;
    let backendErrorDialogOpen = false;

    const BACKEND_FAST_FAIL_MS = 15000;   // muere antes de 15 s = fallo de arranque
    const BACKEND_MAX_FAST_FAILURES = 3;  // 3 seguidos = no reintentar en bucle
    const BACKEND_READY_TIMEOUT_MS = 60000;

    function backendLogPath() {
        try { return path.join(app.getPath('userData'), 'backend.log'); } catch (e) { return null; }
    }

    function appendBackendLog(text) {
        const clean = String(text || '').replace(/\s+$/, '');
        if (!clean) return;
        for (const line of clean.split(/\r?\n/)) {
            backendLogLines.push(`[${new Date().toISOString()}] ${line}`);
        }
        if (backendLogLines.length > 200) backendLogLines = backendLogLines.slice(-200);
        const logPath = backendLogPath();
        if (!logPath) return;
        try { fs.appendFileSync(logPath, clean + '\n'); } catch (e) {}
    }

    function backendErrorDetail() {
        const tail = backendLogLines.slice(-25).join('\n');
        return tail || '(el backend no produjo ninguna salida)';
    }

    async function showBackendErrorDialog(reason) {
        if (backendErrorDialogOpen) return;
        backendErrorDialogOpen = true;
        try {
            if (splashScreen && !splashScreen.isDestroyed()) {
                splashScreen.webContents.executeJavaScript(
                    "var el = document.getElementById('backendState'); if (el) { el.textContent = 'Backend no responde'; }"
                ).catch(() => {});
            }
            const result = await dialog.showMessageBox({
                type: 'error',
                title: 'SonicPush STA - El backend no arranco',
                message: 'El backend no pudo iniciar.',
                detail: reason + '\n\n' + backendErrorDetail() +
                    '\n\nLog completo: ' + (backendLogPath() || '(no disponible)'),
                buttons: ['Reintentar', 'Salir'],
                defaultId: 0,
                cancelId: 1,
                noLink: true
            });
            if (result.response === 0) {
                backendFastFailures = 0;
                backendErrorDialogOpen = false;
                if (!backendProcess || backendProcess.killed) {
                    backendProcess = spawnBackend();
                }
                return;
            }
            app.isQuitting = true;
            app.quit();
        } catch (e) {
            backendErrorDialogOpen = false;
        }
    }

    function spawnBackend() {
        const apiExePath = path.join(appPath, 'api.exe');
        const apiExePathAlt = path.join(appPath, 'api', 'api.exe');
        const apiPyPath = path.join(appPath, 'api.py');
        // Which backend binary to prefer?
        //  - Use the bundled api.exe by default: self-contained Python, works
        //    out-of-the-box on any Windows 10/11 even without python in PATH.
        //  - BUT if api.py is NEWER than api/api.exe, it means the in-app
        //    updater wrote a refreshed api.py that the exe doesn't have yet
        //    -> run api.py with system python so that update takes effect.
        const exeCandidates = [apiExePath, apiExePathAlt].filter(p => fs.existsSync(p));
        const preferPy = fs.existsSync(apiPyPath) &&
            exeCandidates.every(exe => {
                try { return fs.statSync(apiPyPath).mtimeMs > fs.statSync(exe).mtimeMs; }
                catch (e) { return false; }
            });
        let proc;
        backendLastSpawnAt = Date.now();
        if (!preferPy && exeCandidates.length) {
            const exe = exeCandidates[0];
            const cwd = exe === apiExePathAlt ? path.join(appPath, 'api') : appPath;
            proc = spawn(exe, [], { cwd });
        } else if (fs.existsSync(apiPyPath)) {
            proc = spawn('python', [apiPyPath], { cwd: appPath });
        } else if (exeCandidates.length) {
            const exe = exeCandidates[0];
            const cwd = exe === apiExePathAlt ? path.join(appPath, 'api') : appPath;
            proc = spawn(exe, [], { cwd });
        } else {
            proc = spawn('python', ['api.py']); // fallback
        }

        proc.stdout.on('data', (data) => {
            appendBackendLog(data);
            console.log(`[Backend] ${data}`);
        });

        proc.stderr.on('data', (data) => {
            appendBackendLog(data);
            console.error(`[Backend] ${data}`);
        });

        proc.on('error', (err) => {
            const msg = (err && err.message) || String(err);
            appendBackendLog(`No se pudo lanzar el backend: ${msg}`);
            console.error('Backend process error:', err);
            showBackendErrorDialog('No se pudo ejecutar el backend: ' + msg);
        });

        proc.on('exit', (code, signal) => {
            const lifetime = Date.now() - backendLastSpawnAt;
            console.log(`Backend process exited with code ${code} signal ${signal} after ${lifetime}ms`);
            appendBackendLog(`Backend cerrado (code=${code}, signal=${signal}, ${lifetime}ms)`);
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
                backendFastFailures = lifetime < BACKEND_FAST_FAIL_MS ? backendFastFailures + 1 : 0;
                if (backendFastFailures >= BACKEND_MAX_FAST_FAILURES) {
                    showBackendErrorDialog(
                        `El backend se cerro ${backendFastFailures} veces seguidas al arrancar.`
                    );
                    return;
                }
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
        const res = await aiPost('/session', Object.assign({ title: 'SonicPush STA IA' }, aiPermissionRules()), 60000);
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
        const bridgeVersion = pendingSourceUpdateVersion();
        // Compatibilidad automática: si una versión antigua actualizó sólo los
        // archivos JS y reinició, este main ya actualizado completa el salto al
        // instalador binario correcto. No se requiere descarga manual.
        if (bridgeVersion) {
            createSplashScreen();
            try {
                await launchVerifiedInstaller(bridgeVersion);
                clearPendingSourceUpdate();
                setTimeout(() => app.quit(), 400);
                return;
            } catch (error) {
                console.error('Automatic installer bridge failed:', error);
                clearPendingSourceUpdate();
                if (splashScreen && !splashScreen.isDestroyed()) splashScreen.close();
            }
        }
        try { fs.writeFileSync(backendLogPath(), ''); } catch (e) {}
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

