document.addEventListener('DOMContentLoaded', () => {
    let authToken = null;  // Declare authToken at the top

    // Function to wait for the token
    function waitForToken() {
        return new Promise((resolve, reject) => {
            if (authToken) {
                resolve(authToken);
            } else {
                window.electronAPI.onTokenReceived((token) => {
                    authToken = token;
                    resolve(authToken);
                });
            }
        });
    }
    const minBtn = document.getElementById('minimize-btn');
    if (minBtn) {
        minBtn.addEventListener('click', () => {
            window.electronAPI.minimizeApp();
        });
    }

    const closeBtn = document.getElementById('close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            window.electronAPI.closeApp();
        });
    }
    const consoleMinBtn = document.getElementById('consolemin-btn');
    if (consoleMinBtn) {
        consoleMinBtn.addEventListener('click', () => {
            window.electronAPI.minimizeApp();
        });
    }
    const consoleCloseBtn = document.getElementById('consoleclose-btn');
    if (consoleCloseBtn) {
        consoleCloseBtn.addEventListener('click', () => {
            window.electronAPI.send('toggle-console');
        });
    }

    const loginScreen = document.getElementsByClassName('login-box');
    const updateWindow = document.getElementsByClassName('update-content');
    if (loginScreen.length > 0) {
        const responseMessage = document.getElementById('responseMessage');
        const supportBtn = document.getElementById('supportBtn');
        const submitBtn = document.getElementById('submit-button');
        const passwordInput = document.getElementById('password');
        const passwordToggle = document.getElementById('password-toggle');
        const forgotPassword = document.getElementById('forgot-pass');

        passwordToggle.addEventListener('click', function () {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                passwordToggle.classList.add('active');
                passwordToggle.classList.replace('fa-eye', 'fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                passwordToggle.classList.remove('active');
                passwordToggle.classList.replace('fa-eye-slash', 'fa-eye');
            }
        });

        if (supportBtn) {
            supportBtn.addEventListener('click', async (event) => {
                event.preventDefault();
                const url = ''; // URL removed
                window.electronAPI.send('open-external-link', url);
            });
        }

        forgotPassword.addEventListener('click', async (event) => {
            event.preventDefault();
            const url = ''; // URL removed
            window.electronAPI.send('open-external-link', url);
        });

        document.getElementById('submit-button').addEventListener('click', async (event) => {
            event.preventDefault();
            console.log('Submit button clicked'); // Ensure this is firing

            const username = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const stayloggedinboolean = document.getElementById('stay-logged-in').checked;
            let payload;

            payload = { username, password, stayloggedin: stayloggedinboolean };

            const authOption = 'login';
            window.electronAPI.send('login-attempt', { payload, authOption });

            // Handle the response from the main process
            window.electronAPI.receive('login-response', (response) => {
                const responseMessage = document.getElementById('responseMessage');
                if (response.success) {
                    responseMessage.innerHTML = '<span class="success-icon"></span>' + response.message;
                    responseMessage.className = 'success';
                    responseMessage.style.display = 'block';
                    setTimeout(() => {
                        window.electronAPI.send('login-success');
                    }, 500);
                } else {
                    responseMessage.innerHTML = '<span class="error-icon"></span>' + response.message;
                    responseMessage.className = 'error';
                    responseMessage.style.display = 'block';
                }
            });
        });
    }

    else {
        waitForToken().then(() => {

            let startTime;
            let timerInterval;

            loadConfigs();
            loadBatches(null, 'batch-list');
            loadBatches(null, 'batch-list-tidal');
            loadBatches(null, 'batch-list-apple');
            reloadBatchOptions();
            loadSettings();
            hideLoadingModal();

            const configDropdown = document.getElementById('configDropdown');
            const loadConfigButton = document.getElementById('loadConfigButton');

            // Load selected configuration
            loadConfigButton.addEventListener('click', () => {
                const selectedConfig = configDropdown.value;
                fetch(`http://localhost:8999/get_config?name=${selectedConfig}`, {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                })
                    .then(response => response.json())
                    .then(config => {
                        fillConfigForm(config);
                    })
                    .catch(error => {
                        console.error('Error fetching config data:', error);
                    });
            });

            function getLoginStatusIcon(loggedIn) {
                if (loggedIn === null) {
                    // Gray icon (unknown status)
                    return `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ccc" width="24" height="24">
                          <circle cx="12" cy="12" r="10" stroke="gray" stroke-width="2" fill="none"/>
                          <line x1="12" y1="8" x2="12" y2="12" stroke="gray" stroke-width="2"/>
                          <circle cx="12" cy="16" r="1" fill="gray"/>
                        </svg>
                    `;
                } else if (loggedIn) {
                    // Green checkmark (success)
                    return `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="green" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="24" height="24">
                          <path d="M20 6L9 17l-5-5"/>
                        </svg>
                    `;
                } else {
                    // Red cross (failure)
                    return `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="red" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="24" height="24">
                          <line x1="18" y1="6" x2="6" y2="18"/>
                          <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    `;
                }
            }
            

            function openDeviceModal(device, action) {
                const modal = document.getElementById('deviceModal');
                const bindedAccountInput = document.getElementById('modalBindedAccount');
                const bindedProxyInput = document.getElementById('modalBindedProxy');
                const loginButton = document.getElementById('modalLoginButton');
                const checkButton = document.getElementById('modalCheckButton');
                const modalControls = document.getElementById('modalControls');
                const cancelButton = document.getElementById('modalCancelButton');
                const spinner = document.getElementById('loadingSpinner');
                const mainContent = document.getElementById('main-content');

                // Set input fields with existing device info
                bindedAccountInput.value = device.bindedAccount
                bindedProxyInput.value = device.bindedProxy
                

                // Show the modal
                modal.style.display = 'block';

                // Hide or show buttons based on action
                if (action === 'login') {
                    loginButton.style.display = 'inline-block';
                    checkButton.style.display = 'none';
                } else if (action === 'check') {
                    loginButton.style.display = 'none';
                    checkButton.style.display = 'inline-block';
                }

                // Handle the login or check action
                loginButton.onclick = () => {
                    const bindedAccountInput = document.getElementById('modalBindedAccount');
                    const bindedProxyInput = document.getElementById('modalBindedProxy');
                    const launchScrcpyCheckbox = document.getElementById('launchScrcpy');
                
                    // Grab the values from the input fields
                    const account = bindedAccountInput.value;
                    const proxy = bindedProxyInput.value;
                    const launchScrcpy = launchScrcpyCheckbox.checked;
                
                    // Send the device action with the grabbed values
                    modal.style.display = 'none';
                    sendDeviceAction('login', device, account, proxy, launchScrcpy );
                };

                // Handle cancel button
                cancelButton.onclick = () => {
                    modal.style.display = 'none';
                };

                // Close modal when clicking outside the content
                window.onclick = function (event) {
                    if (event.target == modal) {
                        modal.style.display = 'none';
                    }
                };
            }

            
            function sendDeviceAction(action, device, bindedAccount, bindedProxy, launchScrcpy ) {
                const deviceRow = document.querySelector(`tr[data-udid='${device.udid}']`);

                // Check if the device row exists
                if (!deviceRow) {
                    console.error(`Device row not found for UDID: ${device.udid}`);
                    return;
                }

                // Handle 'check' action: replace icon with spinner without opening the modal
                if (action === 'check') {
                    const loggedInCell = deviceRow.querySelector('td:nth-child(7) div');
                    if (!loggedInCell) {
                        console.error(`Logged in status cell not found for device UDID: ${device.udid}`);
                        return;
                    }

                    // Show spinner during the axios request for 'check' action
                    loggedInCell.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                        <circle cx="12" cy="12" r="10" stroke="gray" stroke-width="2" fill="none"/>
                        <path fill="gray" d="M12 2a10 10 0 0110 10h-2a8 8 0 10-8 8v2a10 10 0 010-20z">
                            <animateTransform
                            attributeName="transform"
                            type="rotate"
                            from="0 12 12"
                            to="360 12 12"
                            dur="1s"
                            repeatCount="indefinite"
                            />
                        </path>
                        </svg>
                    `;

                    const payload = {
                        udid: device.udid
                    };

                    // Make the axios request for 'check' action
                    axios.post('http://localhost:8999/device/check', payload, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${authToken}`
                        }
                    })
                    .then(response => {
                        console.log(`Device ${action} successful: `, response.data);

                        const msg = response.data.message || '';
                        const isLoggedIn = msg.toLowerCase().includes("logged in") && !msg.toLowerCase().includes("failed");
                        loggedInCell.innerHTML = getLoginStatusIcon(isLoggedIn);
                        alert(msg || 'Check completed.');
                    })
                    .catch(error => {
                        console.error(`Error during device ${action}: `, error);

                        loggedInCell.innerHTML = getLoginStatusIcon(false);
                        const errData = error.response && error.response.data ? error.response.data : {};
                        const errMsg = errData.message || error.message || 'An unexpected error occurred.';
                        if (error.response) {
                            const accountCell = deviceRow.querySelector('td:nth-child(4)');
                            const proxyCell = deviceRow.querySelector('td:nth-child(5)');

                            if (accountCell) {
                                accountCell.textContent = '/';
                            }
                            if (proxyCell) {
                                proxyCell.textContent = '/';
                            }
                        }
                        alert(errMsg);
                    });

                } else if (action === 'login') {
                    const loggedInCell = deviceRow.querySelector('td:nth-child(7) div');
                    if (!loggedInCell) {
                        console.error(`Logged in status cell not found for device UDID: ${device.udid}`);
                        return;
                    }

                    // Show spinner during the axios request for 'check' action
                    loggedInCell.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                        <circle cx="12" cy="12" r="10" stroke="gray" stroke-width="2" fill="none"/>
                        <path fill="gray" d="M12 2a10 10 0 0110 10h-2a8 8 0 10-8 8v2a10 10 0 010-20z">
                            <animateTransform
                            attributeName="transform"
                            type="rotate"
                            from="0 12 12"
                            to="360 12 12"
                            dur="1s"
                            repeatCount="indefinite"
                            />
                        </path>
                        </svg>
                    `;
                    const payload = {
                        udid: device.udid,
                        bindedAccount: bindedAccount,
                        bindedProxy: bindedProxy,
                        launchScrcpy: launchScrcpy
                    };

                    

                    // Make the axios request for 'login' action
                    axios.post('http://localhost:8999/device/login', payload, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${authToken}`
                        }
                    })
                    .then(response => {
                        console.log(`Device ${action} successful: `, response.data);

                        const msg = response.data.message || '';
                        const isLoggedIn = msg.toLowerCase().includes("logged in") && !msg.toLowerCase().includes("failed");
                        const loggedInCell = deviceRow.querySelector('td:nth-child(7) div');
                        if (loggedInCell) {
                            loggedInCell.innerHTML = getLoginStatusIcon(isLoggedIn);
                        }

                        const accountCell = deviceRow.querySelector('td:nth-child(4)');
                        const proxyCell = deviceRow.querySelector('td:nth-child(5)');

                        if (accountCell) {
                            accountCell.textContent = bindedAccount;
                        }
                        if (proxyCell) {
                            proxyCell.textContent = bindedProxy;
                        }

                        alert(msg || 'Login completed.');
                    })
                    .catch(error => {
                        console.error(`Error during device ${action}: `, error);

                        const loggedInCell = deviceRow.querySelector('td:nth-child(7) div');
                        if (loggedInCell) {
                            loggedInCell.innerHTML = getLoginStatusIcon(false);
                        }
                        const errData = error.response && error.response.data ? error.response.data : {};
                        const errMsg = errData.message || error.message || 'An unexpected error occurred.';
                        alert(errMsg);
                    });
                }
            }

            function parsePhonesInput(raw) {
                // Accepts: "del 1 al 34", "1-34", "1,3,5,7,11,34,66", "1 3 5 7", "1, 5-10", etc.
                const numbers = new Set();
                if (!raw) return [];
                const text = String(raw)
                    .toLowerCase()
                    .replace(/del\s+/g, '')
                    .replace(/\s+al\s+/g, '-')
                    .replace(/al\s+/g, '-')
                    .replace(/\s*,\s*/g, ',')
                    .replace(/\s+/g, ',');
                const tokens = text.split(',');
                for (let t of tokens) {
                    t = t.trim();
                    if (!t) continue;
                    const m = t.match(/^(\d+)\s*-\s*(\d+)$/);
                    if (m) {
                        const a = parseInt(m[1], 10), b = parseInt(m[2], 10);
                        const lo = Math.min(a, b), hi = Math.max(a, b);
                        for (let n = lo; n <= hi; n++) numbers.add(n);
                    } else if (/^\d+$/.test(t)) {
                        numbers.add(parseInt(t, 10));
                    }
                }
                return Array.from(numbers).sort((a, b) => a - b);
            }

            function loadPhonesLoginBatches() {
                const select = document.getElementById('loginAccountsBatch');
                if (!select) return;
                fetch(`http://localhost:8999/get_batches?type=accounts`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                })
                    .then(res => res.json())
                    .then(data => {
                        select.innerHTML = '';
                        if (!data.batches || !data.batches.length) {
                            const opt = document.createElement('option');
                            opt.value = '';
                            opt.textContent = 'No hay batches de cuentas en Manage';
                            select.appendChild(opt);
                            return;
                        }
                        data.batches.forEach(batch => {
                            const opt = document.createElement('option');
                            opt.value = batch.id;
                            opt.textContent = batch.name;
                            select.appendChild(opt);
                        });
                    })
                    .catch(err => console.error('Error loading login batches:', err));
            }

            function startSequentialPhonesLogin(found, accounts, resultDiv) {
                if (!found.length) {
                    resultDiv.innerHTML = '<p style="color: orange;">No hay teléfonos a loguear.</p>';
                    return;
                }
                let html = `<p>Teléfonos a loguear: <b>${found.length}</b></p>`;
                html += '<ul>';
                found.forEach(f => { html += `<li>#${f.num} = ${f.serial} (${f.model})</li>`; });
                html += '</ul>';
                html += '<p style="color: gray;">Iniciando login en cada teléfono con una cuenta del batch (detecta versión e idioma de Spotify en vivo)...</p>';
                resultDiv.innerHTML = html;

                let idx = 0;
                function loginNext() {
                    if (idx >= found.length) {
                        html += '<p><b>Proceso de login terminado.</b></p>';
                        resultDiv.innerHTML = html;
                        return;
                    }
                    const f = found[idx];
                    const account = accounts[idx % accounts.length];
                    let parts = account.split(':');
                    let bindedAccount = parts.slice(0, 2).join(':');
                    let proxy = parts.length >= 3 ? parts.slice(2).join(':') : '/';
                    html += `<p style="color: blue;">[${idx + 1}/${found.length}] Logueando #${f.num} (${f.serial}) con ${bindedAccount}...</p>`;
                    resultDiv.innerHTML = html;
                    axios.post('http://localhost:8999/device/login', {
                        udid: f.serial,
                        bindedAccount: bindedAccount,
                        bindedProxy: proxy,
                        launchScrcpy: false
                    }, {
                        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` }
                    })
                        .then(res => {
                            html += `<p style="color: green;">✓ #${f.num}: ${res.data.message}</p>`;
                            resultDiv.innerHTML = html;
                            idx++;
                            loginNext();
                        })
                        .catch(err => {
                            const msg = (err.response && err.response.data && err.response.data.message) || 'Error';
                            html += `<p style="color: red;">✗ #${f.num}: ${msg}</p>`;
                            resultDiv.innerHTML = html;
                            idx++;
                            loginNext();
                        });
                }
                loginNext();
            }

            function runPhonesLogin() {
                const input = document.getElementById('loginPhonesInput');
                const batchSelect = document.getElementById('loginAccountsBatch');
                const resultDiv = document.getElementById('phonesLoginResult');
                if (!input || !batchSelect || !resultDiv) return;
                const phones = parsePhonesInput(input.value);
                const batchId = batchSelect.value;
                if (!phones.length) {
                    resultDiv.innerHTML = '<p style="color: orange;">No se reconocieron números. Ej: del 1 al 34, o 1,3,5,7,11.</p>';
                    return;
                }
                if (!batchId) {
                    resultDiv.innerHTML = '<p style="color: orange;">Selecciona un batch de cuentas en Manage.</p>';
                    return;
                }

                resultDiv.innerHTML = '<p>Cargando numeración de teléfonos y cuentas...</p>';

                Promise.all([
                    fetch('http://localhost:8999/panda_numbers', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    }).then(r => r.json()),
                    fetch(`http://localhost:8999/get_batches?type=accounts`, {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    }).then(r => r.json()),
                ])
                    .then(([pandaData, batchData]) => {
                        const numMap = {};
                        (pandaData.numbers || []).forEach(p => { numMap[p.num] = p; });

                        const batch = (batchData.batches || []).find(b => String(b.id) === String(batchId));
                        const accounts = (batch ? batch.content : '').split('\n').map(l => l.trim()).filter(l => l !== '');
                        if (!accounts.length) {
                            resultDiv.innerHTML = '<p style="color: orange;">El batch seleccionado no tiene cuentas.</p>';
                            return;
                        }

                        const found = [];
                        const missing = [];
                        phones.forEach(num => {
                            if (numMap[num]) found.push({ num, serial: numMap[num].serial, model: numMap[num].model });
                            else missing.push(num);
                        });

                        if (missing.length) {
                            resultDiv.innerHTML = `<p style="color: orange;">No encontrados: <b>${missing.join(', ')}</b></p>`;
                        }
                        startSequentialPhonesLogin(found, accounts, resultDiv);
                    })
                    .catch(err => {
                        console.error('Error running phones login:', err);
                        resultDiv.innerHTML = '<p style="color: red;">Error: ' + err.message + '</p>';
                    });
            }

            function runPhonesLoginAll() {
                const batchSelect = document.getElementById('loginAccountsBatch');
                const resultDiv = document.getElementById('phonesLoginResult');
                if (!batchSelect || !resultDiv) return;
                const batchId = batchSelect.value;
                if (!batchId) {
                    resultDiv.innerHTML = '<p style="color: orange;">Selecciona un batch de cuentas en Manage.</p>';
                    return;
                }

                resultDiv.innerHTML = '<p>Cargando todos los teléfonos conectados y cuentas...</p>';

                Promise.all([
                    fetch('http://localhost:8999/panda_numbers', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    }).then(r => r.json()),
                    fetch(`http://localhost:8999/get_batches?type=accounts`, {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    }).then(r => r.json()),
                ])
                    .then(([pandaData, batchData]) => {
                        const batch = (batchData.batches || []).find(b => String(b.id) === String(batchId));
                        const accounts = (batch ? batch.content : '').split('\n').map(l => l.trim()).filter(l => l !== '');
                        if (!accounts.length) {
                            resultDiv.innerHTML = '<p style="color: orange;">El batch seleccionado no tiene cuentas.</p>';
                            return;
                        }

                        const found = (pandaData.numbers || []).map(p => ({
                            num: p.num,
                            serial: p.serial,
                            model: p.model
                        }));
                        if (!found.length) {
                            resultDiv.innerHTML = '<p style="color: orange;">No hay teléfonos conectados (revisa Panda/adb).</p>';
                            return;
                        }
                        startSequentialPhonesLogin(found, accounts, resultDiv);
                    })
                    .catch(err => {
                        console.error('Error running login all:', err);
                        resultDiv.innerHTML = '<p style="color: red;">Error: ' + err.message + '</p>';
                    });
            }

            function sendLoginPromptToAI(promptText, resultDiv) {
                if (resultDiv) resultDiv.innerHTML = '<p style="color: gray;">Enviando a la IA...</p>';
                appendChatMessage('user', promptText);
                appendChatThinking();
                const unsubscribe = (window.electronAPI && window.electronAPI.onAiProgress) ? window.electronAPI.onAiProgress(function(txt) {
                    updateChatThinking(txt);
                    if (resultDiv) {
                        const safe = String(txt || '').replace(/</g, '&lt;').slice(0, 3000);
                        resultDiv.innerHTML = '<p style="color: gray;"><b>IA trabajando:</b><br><pre style="white-space:pre-wrap;">' + safe + '</pre></p>';
                    }
                }) : null;
                window.electronAPI.aiChat({ text: promptText })
                    .then(res => {
                        removeChatThinking();
                        if (res && res.ok) {
                            if (resultDiv) resultDiv.innerHTML = '<p style="color: green;"><b>IA terminó.</b><br><pre style="white-space:pre-wrap;">' + String(res.text || '').replace(/</g, '&lt;').slice(0, 5000) + '</pre></p>';
                            appendChatMessage('assistant', res.text || '(sin respuesta)');
                            setChatStatus('ready', 'IA lista · Modelo big-pickle');
                        } else {
                            if (resultDiv) resultDiv.innerHTML = '<p style="color: red;">Error: ' + ((res && res.error) || 'Error desconocido') + '</p>';
                            appendChatMessage('error', (res && res.error) || 'Error desconocido');
                            setChatStatus('error', 'IA con error');
                        }
                    })
                    .catch(err => {
                        removeChatThinking();
                        if (resultDiv) resultDiv.innerHTML = '<p style="color: red;">Error: ' + (err && err.message ? err.message : String(err)) + '</p>';
                        appendChatMessage('error', err && err.message ? err.message : String(err));
                        setChatStatus('error', 'IA con error');
                    })
                    .finally(function() {
                        if (typeof unsubscribe === 'function') unsubscribe();
                    });
            }

            function batchSelectedName() {
                const s = document.getElementById('loginAccountsBatch');
                if (s && s.selectedOptions && s.selectedOptions.length) return s.selectedOptions[0].textContent;
                return '';
            }

            document.getElementById('runPhonesLoginButton').addEventListener('click', function() {
                const input = document.getElementById('loginPhonesInput');
                const batchSelect = document.getElementById('loginAccountsBatch');
                const resultDiv = document.getElementById('phonesLoginResult');
                if (!input || !batchSelect || !resultDiv) return;
                const phones = parsePhonesInput(input.value);
                if (!phones.length) {
                    resultDiv.innerHTML = '<p style="color: orange;">No se reconocieron números. Ej: del 1 al 34, o 1,3,5,7,11.</p>';
                    return;
                }
                if (!batchSelect.value) {
                    resultDiv.innerHTML = '<p style="color: orange;">Selecciona un batch de cuentas en Manage.</p>';
                    return;
                }
                const prompt = 'Haz login en los teléfonos con numeración de Panda: ' + phones.join(', ') +
                    '. Usa las cuentas del batch "' + batchSelectedName() + '" de la app. ' +
                    'Si Spotify pide un código de verificación, pícale en "Iniciar sesión con contraseña" o "log in with a password" ' +
                    'y completa el login con la contraseña de la cuenta. Verifica cada login y reporta el resultado de cada teléfono.';
                sendLoginPromptToAI(prompt, resultDiv);
            });

            document.getElementById('runPhonesLoginAllButton').addEventListener('click', function() {
                const batchSelect = document.getElementById('loginAccountsBatch');
                const resultDiv = document.getElementById('phonesLoginResult');
                if (!batchSelect || !resultDiv) return;
                if (!batchSelect.value) {
                    resultDiv.innerHTML = '<p style="color: orange;">Selecciona un batch de cuentas en Manage.</p>';
                    return;
                }
                const prompt = 'Haz login en TODOS los teléfonos conectados (numeración de Panda). ' +
                    'Usa las cuentas del batch "' + batchSelectedName() + '" de la app. ' +
                    'Si Spotify pide un código de verificación, pícale en "Iniciar sesión con contraseña" o "log in with a password" ' +
                    'y completa el login con la contraseña de la cuenta. Verifica cada login y reporta el resultado de cada teléfono.';
                sendLoginPromptToAI(prompt, resultDiv);
            });

            loadPhonesLoginBatches();

            function loadPhonesLoginBatchesTidal() {
                const select = document.getElementById('loginAccountsBatchTidal');
                if (!select) return;
                fetch(`http://localhost:8999/get_batches?type=tidal_accounts`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                })
                    .then(res => res.json())
                    .then(data => {
                        select.innerHTML = '';
                        if (!data.batches || !data.batches.length) {
                            const opt = document.createElement('option');
                            opt.value = '';
                            opt.textContent = 'No hay batches de cuentas Tidal en Manage';
                            select.appendChild(opt);
                            return;
                        }
                        data.batches.forEach(batch => {
                            const opt = document.createElement('option');
                            opt.value = batch.id;
                            opt.textContent = batch.name;
                            select.appendChild(opt);
                        });
                    })
                    .catch(err => console.error('Error loading tidal login batches:', err));
            }
            loadPhonesLoginBatchesTidal();

            function loadPhonesLoginBatchesApple() {
                const select = document.getElementById('loginAccountsBatchApple');
                if (!select) return;
                fetch(`http://localhost:8999/get_batches?type=apple_accounts`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                })
                    .then(res => res.json())
                    .then(data => {
                        select.innerHTML = '';
                        if (!data.batches || !data.batches.length) {
                            const opt = document.createElement('option');
                            opt.value = '';
                            opt.textContent = 'No hay batches de cuentas Apple Music en Manage';
                            select.appendChild(opt);
                            return;
                        }
                        data.batches.forEach(batch => {
                            const opt = document.createElement('option');
                            opt.value = batch.id;
                            opt.textContent = batch.name;
                            select.appendChild(opt);
                        });
                    })
                    .catch(err => console.error('Error loading apple login batches:', err));
            }
            loadPhonesLoginBatchesApple();

            document.getElementById('runPhonesLoginButtonTidal').addEventListener('click', function() {
                const input = document.getElementById('loginPhonesInputTidal');
                const batchSelect = document.getElementById('loginAccountsBatchTidal');
                const resultDiv = document.getElementById('phonesLoginResultTidal');
                if (!input || !batchSelect || !resultDiv) return;
                const phones = parsePhonesInput(input.value);
                if (!phones.length) {
                    resultDiv.innerHTML = '<p style="color: orange;">No se reconocieron números. Ej: del 1 al 34, o 1,3,5,7,11.</p>';
                    return;
                }
                if (!batchSelect.value) {
                    resultDiv.innerHTML = '<p style="color: orange;">Selecciona un batch de cuentas Tidal en Manage.</p>';
                    return;
                }
                const batchName = batchSelect.selectedOptions[0] ? batchSelect.selectedOptions[0].textContent : '';
                const prompt = 'Haz login en los teléfonos con numeración de Panda: ' + phones.join(', ') + ' en la app Tidal. ' +
                    'Usa las cuentas del batch "' + batchName + '" de la app. ' +
                    'Abre Tidal en cada teléfono y completa el login con email y contraseña. Verifica cada login y reporta el resultado.';
                sendLoginPromptToAI(prompt, resultDiv);
            });

            document.getElementById('runPhonesLoginButtonApple').addEventListener('click', function() {
                const input = document.getElementById('loginPhonesInputApple');
                const batchSelect = document.getElementById('loginAccountsBatchApple');
                const resultDiv = document.getElementById('phonesLoginResultApple');
                if (!input || !batchSelect || !resultDiv) return;
                const phones = parsePhonesInput(input.value);
                if (!phones.length) {
                    resultDiv.innerHTML = '<p style="color: orange;">No se reconocieron números. Ej: del 1 al 34, o 1,3,5,7,11.</p>';
                    return;
                }
                if (!batchSelect.value) {
                    resultDiv.innerHTML = '<p style="color: orange;">Selecciona un batch de cuentas Apple Music en Manage.</p>';
                    return;
                }
                const batchName = batchSelect.selectedOptions[0] ? batchSelect.selectedOptions[0].textContent : '';
                const prompt = 'Haz login en los teléfonos con numeración de Panda: ' + phones.join(', ') + ' en Apple Music. ' +
                    'Usa las cuentas del batch "' + batchName + '" de la app. ' +
                    'Abre Apple Music en cada teléfono y completa el login con email y contraseña. Verifica cada login y reporta el resultado.';
                sendLoginPromptToAI(prompt, resultDiv);
            });

            document.getElementById('scrapeDevicesButton').addEventListener('click', function() {
                fetchDevices(); // Reuse the function to fetch and display the devices after scraping
            });

            document.getElementById('patchSpotifyButton').addEventListener('click', function() {
                const btn = this;
                const original = btn.textContent;
                btn.disabled = true;
                btn.textContent = 'Aplicando fix screen...';
                axios.post('http://localhost:8999/patch_spotify', {}, {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    }
                })
                .then(response => {
                    alert(response.data.message);
                })
                .catch(error => {
                    console.error('Error applying fix screen:', error);
                    if (error.response && error.response.data) {
                        alert(error.response.data.message);
                    } else {
                        alert('Error al aplicar fix screen: no response from server.');
                    }
                })
                .finally(() => {
                    btn.disabled = false;
                    btn.textContent = original;
                });
            });

            function fetchDevices() {
                // Show loading modal and blur main content
                const loadingModal = document.getElementById('loadingModal');
                const mainContent = document.getElementById('main-content');
                if (loadingModal && mainContent) {
                    loadingModal.style.display = 'block';
                    mainContent.classList.add('blurred');
                }
            
                fetch('http://localhost:8999/scrape_devices', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}` // Add the token here
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('scrapeDevicesLen').textContent = `Connected Devices: ${data.devices.length}`;
                        const devicesTableBody = document.querySelector('#devicesTable tbody');
                        devicesTableBody.innerHTML = ''; // Clear existing rows
            
                        data.devices.forEach(device => {
                            const row = document.createElement('tr');
                            row.setAttribute('data-udid', device.udid);
            
                            const udidCell = document.createElement('td');
                            udidCell.textContent = device.udid;
                            row.appendChild(udidCell);
            
                            // Create and populate the table cells for Manufacturer
                            const manufacturerCell = document.createElement('td');
                            manufacturerCell.textContent = device.manufacturer || 'Unknown';
                            row.appendChild(manufacturerCell);
            
                            // Create and populate the table cells for Model
                            const modelCell = document.createElement('td');
                            modelCell.textContent = device.model || 'Unknown';
                            row.appendChild(modelCell);
            
                            // Create and populate the table cells for Binded Account
                            const accountCell = document.createElement('td');
                            accountCell.contentEditable = true;
                            accountCell.textContent = device.bindedAccount || 'Not binded';
                            row.appendChild(accountCell);
            
                            // Create and populate the table cells for Binded Proxy
                            const proxyCell = document.createElement('td');
                            proxyCell.contentEditable = true;
                            proxyCell.textContent = device.bindedProxy || 'Not binded';
                            row.appendChild(proxyCell);

                            accountCell.addEventListener('blur', () => {
                                const newAccount = accountCell.textContent.trim();
                                updateDevice(device.udid, { bindedAccount: newAccount });
                            });

                            proxyCell.addEventListener('blur', () => {
                                const newProxy = proxyCell.textContent.trim();
                                updateDevice(device.udid, { bindedProxy: newProxy });
                            });


                            const controlsCell = document.createElement('td');
                            const loginButton = document.createElement('button');
                            loginButton.textContent = 'Login';
                            loginButton.classList.add('boton-elegante');
                            loginButton.addEventListener('click', () => openDeviceModal(device, 'login'));
            
                            const checkButton = document.createElement('button');
                            checkButton.textContent = 'Check';
                            checkButton.classList.add('boton-elegante');
                            checkButton.addEventListener('click', () => sendDeviceAction('check', device, null, null, false));
            
                            controlsCell.appendChild(loginButton);
                            controlsCell.appendChild(checkButton);
                            row.appendChild(controlsCell);
            
                            const loggedInCell = document.createElement('td');
                            const svgIcon = document.createElement('div');
                            svgIcon.innerHTML = getLoginStatusIcon(device.logged_in); // Call the function to get the correct SVG based on status
                            loggedInCell.appendChild(svgIcon);
                            row.appendChild(loggedInCell);
            
                            // Add the row to the table body
                            devicesTableBody.appendChild(row);
                        });
            
                        // Hide loading modal and remove blur
                        if (loadingModal && mainContent) {
                            loadingModal.style.display = 'none';
                            mainContent.classList.remove('blurred');
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching devices:', error);
            
                        // Hide loading modal and remove blur in case of an error
                        if (loadingModal && mainContent) {
                            loadingModal.style.display = 'none';
                            mainContent.classList.remove('blurred');
                        }
                    });
            }
            
            
            function updateDevice(udid, updatedData) {
                fetch('http://localhost:8999/update_device', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify({
                        udid: udid,
                        ...updatedData
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Device updated:', data.message);
                })
                .catch(error => {
                    console.error('Error updating device:', error);
                });
            }


            function fillConfigForm(config) {
                document.getElementById('config-name').value = config.config_name;
                document.getElementById('streams-to-do').value = config.streams_to_do;
                document.getElementById('album-likes-rate').value = config.album_likes_rate;
                document.getElementById('song-likes-rate').value = config.song_likes_rate;
                document.getElementById('follows-rate').value = config.follows_rate;
                document.getElementById('full-playtime-rate').value = config.full_playtime_rate;
                document.getElementById('playtime-seconds').value = config.playtime_seconds;
                document.getElementById('spotify-playtime').value = config.spotify_playtime || '';
                document.getElementById('tidal-playtime').value = config.tidal_playtime || '';
                document.getElementById('apple-playtime').value = config.apple_playtime || '';
                document.getElementById('streaming-mode-only').value = config.streaming_mode_only;
                document.getElementById('links-select').value = config.links_batch_id || '';
                document.getElementById('shuffle-perc').value = config.shuffle_perc;
                document.getElementById('search-links-perc').value = config.search_links_perc;
                if (document.getElementById('tidal-links-select'))
                    document.getElementById('tidal-links-select').value = config.tidal_links_batch_id || '';
                if (document.getElementById('tidal-shuffle-perc'))
                    document.getElementById('tidal-shuffle-perc').value = config.tidal_shuffle_perc || 0;
                if (document.getElementById('tidal-search-links-perc'))
                    document.getElementById('tidal-search-links-perc').value = config.tidal_search_links_perc || 0;
                if (document.getElementById('apple-links-select'))
                    document.getElementById('apple-links-select').value = config.apple_links_batch_id || '';
                if (document.getElementById('apple-shuffle-perc'))
                    document.getElementById('apple-shuffle-perc').value = config.apple_shuffle_perc || 0;
                if (document.getElementById('apple-search-links-perc'))
                    document.getElementById('apple-search-links-perc').value = config.apple_search_links_perc || 0;
                document.getElementById('session-time').value = config.session_time;
                document.getElementById('use-webhook').checked = config.webhook.use;
                document.getElementById('webhook-name').value = config.webhook.name;
                document.getElementById('webhook-url').value = config.webhook.url;
                document.getElementById('webhook-interval').value = config.webhook.interval;

                const selectedApps = config.selected_apps || ['spotify'];
                document.getElementById('app-spotify').checked = selectedApps.includes('spotify');
                document.getElementById('app-apple-music').checked = selectedApps.includes('apple_music');
                document.getElementById('app-tidal').checked = selectedApps.includes('tidal');

                toggleWebhook(document.getElementById('use-webhook'));
            }


            const useWebhookCheckbox = document.getElementById('use-webhook');
            if (useWebhookCheckbox) {
                useWebhookCheckbox.addEventListener('change', function() {
                    toggleWebhook(this);
                });
            }

            // Initial call to set the correct visibility based on the initial state
            toggleWebhook(useWebhookCheckbox);


            document.getElementById('showConsole').addEventListener('click', () => {
                window.electronAPI.send('toggle-console');
            });

            // Listen for console toggle reply from main process
            window.electronAPI.receive('console-toggled', (message) => {
                document.getElementById('showConsole').textContent = message;
            });

            // Attach event listeners to all form inputs for auto-save in the Settings tab
            const settingsFormElements = document.querySelectorAll('#settingsForm input');

            settingsFormElements.forEach(element => {
                element.addEventListener('input', () => {
                    saveCurrentSettings();
                });
            });

            // ---- Install Apps ----
            (function() {
                const btn = document.getElementById('installAppsButton');
                if (!btn) return;
                btn.addEventListener('click', function() {
                    const input = document.getElementById('installPhonesInput');
                    const resultDiv = document.getElementById('installAppsResult');
                    if (!input || !resultDiv) return;
                    const phones = parsePhonesInput(input.value);
                    if (!phones.length) {
                        resultDiv.innerHTML = '<p style="color: orange;">No se reconocieron numeros. Ej: del 1 al 10, o 1,3,5,7.</p>';
                        return;
                    }
                    const apps = [];
                    if (document.getElementById('installSpotifyCheck').checked) apps.push('spotify');
                    if (document.getElementById('installTidalCheck').checked) apps.push('tidal');
                    if (document.getElementById('installAppleCheck').checked) apps.push('apple_music');
                    if (!apps.length) {
                        resultDiv.innerHTML = '<p style="color: orange;">Selecciona al menos una app.</p>';
                        return;
                    }
                    resultDiv.innerHTML = '<p style="color: gray;">Instalando en ' + phones.length + ' dispositivos...</p>';
                    btn.disabled = true;
                    fetch('http://localhost:8999/install_apps', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + authToken
                        },
                        body: JSON.stringify({ phones: phones, apps: apps })
                    })
                    .then(r => r.json())
                    .then(data => {
                        btn.disabled = false;
                        if (data.success) {
                            let html = '<p style="color: green;"><b>Instalacion completada.</b></p><ul>';
                            if (data.results) {
                                data.results.forEach(r => {
                                    const color = r.success ? 'green' : 'red';
                                    html += '<li style="color:' + color + ';">' + r.device + ' - ' + r.app + ': ' + (r.message || (r.success ? 'OK' : 'Error')) + '</li>';
                                });
                            }
                            html += '</ul>';
                            resultDiv.innerHTML = html;
                        } else {
                            resultDiv.innerHTML = '<p style="color: red;">Error: ' + (data.error || 'Error desconocido') + '</p>';
                        }
                    })
                    .catch(err => {
                        btn.disabled = false;
                        resultDiv.innerHTML = '<p style="color: red;">Error de conexion: ' + (err.message || err) + '</p>';
                    });
                });
            })();

            // ---- Update System ----
            (function() {
                const checkBtn = document.getElementById('checkUpdateButton');
                const installBtn = document.getElementById('installUpdateButton');
                const statusDiv = document.getElementById('updateStatus');
                const resultDiv = document.getElementById('updateResult');
                const notesSection = document.getElementById('updateNotesSection');
                const notesDiv = document.getElementById('updateNotes');
                const versionLabel = document.getElementById('updateCurrentVersion');
                if (!checkBtn) return;

                fetch('http://localhost:8999/get_version', {
                    headers: { 'Authorization': 'Bearer ' + authToken }
                })
                .then(r => r.json())
                .then(d => { if (versionLabel && d.version) versionLabel.textContent = 'Current version: ' + d.version; })
                .catch(() => {});

                let pendingRemoteVersion = null;

                checkBtn.addEventListener('click', function() {
                    checkBtn.disabled = true;
                    checkBtn.textContent = 'Checking...';
                    statusDiv.innerHTML = '<p style="color: gray;">Connecting to GitHub...</p>';
                    resultDiv.innerHTML = '';
                    notesSection.style.display = 'none';
                    installBtn.style.display = 'none';
                    pendingRemoteVersion = null;

                    fetch('http://localhost:8999/check_update', {
                        headers: { 'Authorization': 'Bearer ' + authToken }
                    })
                    .then(r => r.json())
                    .then(data => {
                        checkBtn.disabled = false;
                        checkBtn.textContent = 'Check for Updates';
                        if (data.error) {
                            statusDiv.innerHTML = '<p style="color: red;">Error: ' + data.error + '</p>';
                            return;
                        }
                        if (data.has_update) {
                            statusDiv.innerHTML = '<p style="color: #2ecc71; font-weight:bold;">Update available: v' + data.remote_version + '</p>';
                            resultDiv.innerHTML = '<p style="color: gray;">Your version: v' + data.current_version + ' → New: v' + data.remote_version + '</p>';
                            if (data.release_notes) {
                                notesDiv.textContent = data.release_notes;
                                notesSection.style.display = 'block';
                            }
                            pendingRemoteVersion = data.remote_version;
                            installBtn.style.display = 'inline-block';
                        } else {
                            statusDiv.innerHTML = '<p style="color: #2ecc71;">You are up to date! (v' + data.current_version + ')</p>';
                        }
                    })
                    .catch(err => {
                        checkBtn.disabled = false;
                        checkBtn.textContent = 'Check for Updates';
                        statusDiv.innerHTML = '<p style="color: red;">Connection error: ' + (err.message || err) + '</p>';
                    });
                });

                installBtn.addEventListener('click', function() {
                    if (!pendingRemoteVersion) return;
                    if (!confirm('The app will update and restart. Continue?')) return;
                    installBtn.disabled = true;
                    installBtn.textContent = 'Updating...';
                    statusDiv.innerHTML = '<p style="color: gray;">Downloading updated files...</p>';

                    fetch('http://localhost:8999/install_update', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + authToken
                        },
                        body: JSON.stringify({ remote_version: pendingRemoteVersion })
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            statusDiv.innerHTML = '<p style="color: #2ecc71;">Updated to v' + pendingRemoteVersion + '! Restarting...</p>';
                            setTimeout(() => {
                                if (window.electronAPI && window.electronAPI.restartApp) {
                                    window.electronAPI.restartApp();
                                }
                            }, 1500);
                        } else {
                            statusDiv.innerHTML = '<p style="color: red;">Error: ' + (data.error || 'Unknown') + '</p>';
                            installBtn.disabled = false;
                            installBtn.textContent = 'Install Update';
                        }
                    })
                    .catch(err => {
                        statusDiv.innerHTML = '<p style="color: red;">Error: ' + (err.message || err) + '</p>';
                        installBtn.disabled = false;
                        installBtn.textContent = 'Install Update';
                    });
                });
            })();

            document.getElementById('startDate').addEventListener('change', updateChart);
            document.getElementById('endDate').addEventListener('change', updateChart);
            showTab('home');

            const sidebarButtons = {
                homeBtn: 'home',
                loginBtn: 'login',
                devicesBtn: 'devices',
                manageBtn: 'manage',
                configBtn: 'config',
                analyticsBtn: 'analytics',
                settingsBtn: 'settings',
                chatBtn: 'chat'
            };

            Object.keys(sidebarButtons).forEach(buttonId => {
                const button = document.getElementById(buttonId);
                const tabName = sidebarButtons[buttonId];
                if (button) {
                    button.addEventListener('click', () => showTab(tabName));
                }
            });

            // ---- IA Chat ----
            const chatMessages = document.getElementById('chatMessages');
            const chatInput = document.getElementById('chatInput');
            const chatSendButton = document.getElementById('chatSendButton');
            const chatResetButton = document.getElementById('chatResetButton');
            const chatStatusDot = document.getElementById('chatStatusDot');
            const chatStatusText = document.getElementById('chatStatusText');
            let chatPending = false;

            function setChatStatus(state, label) {
                if (chatStatusDot) {
                    chatStatusDot.classList.remove('ready', 'error');
                    if (state === 'ready') chatStatusDot.classList.add('ready');
                    if (state === 'error') chatStatusDot.classList.add('error');
                }
                if (chatStatusText) chatStatusText.textContent = label;
            }

            function appendChatMessage(role, text) {
                if (!chatMessages) return;
                const el = document.createElement('div');
                el.className = 'chat-msg ' + role;
                const label = document.createElement('span');
                label.className = 'role-label';
                label.textContent = role === 'user' ? 'Tú' : (role === 'assistant' ? 'IA' : 'Error');
                el.appendChild(label);
                const body = document.createElement('div');
                body.textContent = text;
                el.appendChild(body);
                chatMessages.appendChild(el);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            function appendChatThinking() {
                if (!chatMessages) return null;
                const el = document.createElement('div');
                el.className = 'chat-thinking';
                el.id = 'chatThinking';
                const spinner = document.createElement('div');
                spinner.className = 'spinner';
                el.appendChild(spinner);
                const label = document.createElement('span');
                label.className = 'thinking-label';
                label.textContent = 'Trabajando...';
                el.appendChild(label);
                const progress = document.createElement('div');
                progress.className = 'thinking-progress';
                progress.textContent = '';
                el.appendChild(progress);
                chatMessages.appendChild(el);
                chatMessages.scrollTop = chatMessages.scrollHeight;
                return el;
            }

            function updateChatThinking(text) {
                const el = document.getElementById('chatThinking');
                if (!el) return;
                const prog = el.querySelector('.thinking-progress');
                if (!prog) return;
                prog.textContent = text && text.trim() ? text.trim().slice(0, 300) : '';
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            function removeChatThinking() {
                const el = document.getElementById('chatThinking');
                if (el) el.remove();
            }

            async function sendChatMessage() {
                if (!chatInput || !chatSendButton) return;
                const text = chatInput.value.trim();
                if (!text || chatPending) return;
                chatPending = true;
                chatInput.value = '';
                chatSendButton.disabled = true;
                appendChatMessage('user', text);
                appendChatThinking();
                const unsubscribe = (window.electronAPI && window.electronAPI.onAiProgress) ? window.electronAPI.onAiProgress(updateChatThinking) : null;
                try {
                    const res = await window.electronAPI.aiChat({ text });
                    removeChatThinking();
                    if (res && res.ok) {
                        appendChatMessage('assistant', res.text || '(sin respuesta)');
                        setChatStatus('ready', 'IA lista · Modelo big-pickle');
                    } else {
                        appendChatMessage('error', (res && res.error) || 'Error desconocido');
                        setChatStatus('error', 'IA con error');
                    }
                } catch (err) {
                    removeChatThinking();
                    appendChatMessage('error', err && err.message ? err.message : String(err));
                    setChatStatus('error', 'IA con error');
                } finally {
                    if (typeof unsubscribe === 'function') unsubscribe();
                    chatPending = false;
                    chatSendButton.disabled = false;
                    chatInput.focus();
                }
            }

            async function refreshChatStatus() {
                try {
                    const st = await window.electronAPI.aiStatus();
                    if (st && st.ready) {
                        setChatStatus('ready', 'IA lista · Modelo ' + st.model);
                    } else {
                        setChatStatus('error', 'IA no disponible');
                    }
                } catch (e) {
                    setChatStatus('error', 'IA no disponible');
                }
            }

            if (chatSendButton) chatSendButton.addEventListener('click', sendChatMessage);
            if (chatResetButton) chatResetButton.addEventListener('click', async () => {
                await window.electronAPI.aiReset();
                chatMessages.innerHTML = '';
                refreshChatStatus();
            });
            if (chatInput) {
                chatInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendChatMessage();
                    }
                });
            }
            refreshChatStatus();

            const startStopButton = document.getElementById('startStopButton');
            if (startStopButton) {
                startStopButton.addEventListener('click', () => startBot());
            }

            const saveConfigButton = document.getElementById('saveConfigButton');
            if (saveConfigButton) {
                saveConfigButton.addEventListener('click', saveConfig);
            }

            // Event listener for batch type selection (Spotify)
            const batchTypeSelect = document.getElementById('batch-type');
            if (batchTypeSelect) {
                batchTypeSelect.addEventListener('change', () => loadBatches(null, 'batch-list'));
            }

            // Event listener for adding new batch (Spotify)
            const addBatchButton = document.getElementById('addBatchButton');
            if (addBatchButton) {
                addBatchButton.addEventListener('click', () => showAddBatchModal('batch-type', 'batch-list'));
            }

            // Event listener for batch type selection (Tidal)
            const batchTypeTidal = document.getElementById('batch-type-tidal');
            if (batchTypeTidal) {
                batchTypeTidal.addEventListener('change', () => loadBatches(null, 'batch-list-tidal'));
            }

            // Event listener for adding new batch (Tidal)
            const addBatchButtonTidal = document.getElementById('addBatchButtonTidal');
            if (addBatchButtonTidal) {
                addBatchButtonTidal.addEventListener('click', () => showAddBatchModal('batch-type-tidal', 'batch-list-tidal'));
            }

            // Event listener for batch type selection (Apple)
            const batchTypeApple = document.getElementById('batch-type-apple');
            if (batchTypeApple) {
                batchTypeApple.addEventListener('change', () => loadBatches(null, 'batch-list-apple'));
            }

            // Event listener for adding new batch (Apple)
            const addBatchButtonApple = document.getElementById('addBatchButtonApple');
            if (addBatchButtonApple) {
                addBatchButtonApple.addEventListener('click', () => showAddBatchModal('batch-type-apple', 'batch-list-apple'));
            }

            // Event listener for saving a new batch in the modal
            const batchModalSaveButton = document.getElementById('batchModalSaveButton');
            if (batchModalSaveButton) {
                batchModalSaveButton.addEventListener('click', saveNewBatch);
            }

            // Event listener for canceling batch modal
            const batchModalCancelButton = document.getElementById('batchModalCancelButton');
            if (batchModalCancelButton) {
                batchModalCancelButton.addEventListener('click', closeAddBatchModal);
            }

            // Event listener for closing batch modal
            const batchModalCloseButton = document.getElementById('batchModalCloseButton');
            if (batchModalCloseButton) {
                batchModalCloseButton.addEventListener('click', closeAddBatchModal);
            }

            // Event listener for closing loading modal
            const loadingModalCloseButton = document.getElementById('loadingModalCloseButton');
            if (loadingModalCloseButton) {
                loadingModalCloseButton.addEventListener('click', hideLoadingModal);
            }

            function showTab(tabName) {
                // Hide all tabs
                const tabs = document.querySelectorAll('.content-tab, .content-tab-scrollable');
                tabs.forEach(tab => {
                    tab.classList.remove('active');
                });

                // Get the tab to show
                const tabToShow = document.getElementById(tabName);
                if (tabToShow) {
                    tabToShow.classList.add('active');
                } else {
                    console.error(`Tab with ID ${tabName} does not exist.`);
                }

                // Update the active button in the sidebar
                const buttons = document.querySelectorAll('#sidebar button');
                buttons.forEach(button => {
                    button.classList.remove('active');
                });

                const activeButton = document.getElementById(tabName + 'Btn');
                if (activeButton) {
                    activeButton.classList.add('active');
                } else {
                    console.error(`Button with ID ${tabName + 'Btn'} does not exist.`);
                }

                // Load settings if the settings tab is shown
                if (tabName === 'settings') {
                    loadSettings();
                }
                if (tabName === 'chat') {
                    refreshChatStatus();
                }
            }

            function saveConfig() {
                const selectedApps = [];
                if (document.getElementById('app-spotify').checked) selectedApps.push('spotify');
                if (document.getElementById('app-apple-music').checked) selectedApps.push('apple_music');
                if (document.getElementById('app-tidal').checked) selectedApps.push('tidal');

                const configData = {
                    config_name: document.getElementById('config-name').value,
                    streams_to_do: document.getElementById('streams-to-do').value,
                    album_likes_rate: document.getElementById('album-likes-rate').value,
                    song_likes_rate: document.getElementById('song-likes-rate').value,
                    follows_rate: document.getElementById('follows-rate').value,
                    full_playtime_rate: document.getElementById('full-playtime-rate').value,
                    playtime_seconds: document.getElementById('playtime-seconds').value,
                    spotify_playtime: document.getElementById('spotify-playtime').value || '',
                    tidal_playtime: document.getElementById('tidal-playtime').value || '',
                    apple_playtime: document.getElementById('apple-playtime').value || '',
                    streaming_mode_only: document.getElementById('streaming-mode-only').checked,
                    links_batch_id: document.getElementById('links-select').value,
                    shuffle_perc: document.getElementById('shuffle-perc').value,
                    search_links_perc: document.getElementById('search-links-perc').value,
                    tidal_links_batch_id: document.getElementById('tidal-links-select') ? document.getElementById('tidal-links-select').value : '',
                    tidal_shuffle_perc: document.getElementById('tidal-shuffle-perc') ? document.getElementById('tidal-shuffle-perc').value : 0,
                    tidal_search_links_perc: document.getElementById('tidal-search-links-perc') ? document.getElementById('tidal-search-links-perc').value : 0,
                    apple_links_batch_id: document.getElementById('apple-links-select') ? document.getElementById('apple-links-select').value : '',
                    apple_shuffle_perc: document.getElementById('apple-shuffle-perc') ? document.getElementById('apple-shuffle-perc').value : 0,
                    apple_search_links_perc: document.getElementById('apple-search-links-perc') ? document.getElementById('apple-search-links-perc').value : 0,
                    session_time: document.getElementById('session-time').value,
                    selected_apps: selectedApps,
                    webhook: {
                        use: document.getElementById('use-webhook').checked,
                        name: document.getElementById('webhook-name').value,
                        url: document.getElementById('webhook-url').value,
                        interval: document.getElementById('webhook-interval').value
                    }
                };

                fetch('http://localhost:8999/save_config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}` // Add the token here
                    },
                    body: JSON.stringify(configData)
                })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        loadConfigs();
                    })
                    .catch(error => {
                        console.error('Error:', error);
                    });
            }

            let workerIntervalId = null;
            let statsIntervalId = null;

            function clearBotIntervals() {
                if (workerIntervalId) {
                    clearInterval(workerIntervalId);
                    workerIntervalId = null;
                }
                if (statsIntervalId) {
                    clearInterval(statsIntervalId);
                    statsIntervalId = null;
                }
            }

            function startBot() {
                const configName = document.getElementById('configSelect').value;
                const button = document.getElementById('startStopButton');

                fetch('http://localhost:8999/start_bot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify({ config_name: configName })
                })
                    .then(async response => {
                        let data;
                        try {
                            data = await response.json();
                        } catch (e) {
                            alert('Error: Server returned invalid response');
                            return;
                        }
                        if (!response.ok) {
                            alert(data.message || 'Error');
                            return;
                        }
                        if (button.textContent === 'Stop') {
                            clearBotIntervals();
                            toggleStartStopButton();
                        } else {
                            fetchWorkerThreads();
                            if (workerIntervalId) clearInterval(workerIntervalId);
                            workerIntervalId = setInterval(fetchWorkerThreads, 5000);
                            fetchWorkerStats();
                            if (statsIntervalId) clearInterval(statsIntervalId);
                            statsIntervalId = setInterval(fetchWorkerStats, 5000);
                            fetchDashboard();
                            setInterval(fetchDashboard, 8000);
                            toggleStartStopButton();
                            startTimer();
                        }
                    })
                    .catch(error => {
                        alert('Error: ' + error.message);
                    });
            }

            function loadBatchOptions(selectId, batchType) {
                fetch(`http://localhost:8999/get_batches?type=${batchType}`, {
                    headers: {
                        'Authorization': `Bearer ${authToken}` // Add the token here
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        const select = document.getElementById(selectId);
                        select.innerHTML = '';
                        data.batches.forEach(batch => {
                            const option = document.createElement('option');
                            option.value = batch.id;
                            option.textContent = batch.name;
                            select.appendChild(option);
                        });
                    })
                    .catch(error => {
                        console.error('Error loading batch options:', error);
                    });
            }

            function loadConfigs() {
                fetch('http://localhost:8999/get_configs', {
                    headers: {
                        'Authorization': `Bearer ${authToken}` // Add the token here
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        const configDropdown = document.getElementById('configDropdown'); // Assuming you're using this ID
                        const configSelect = document.getElementById('configSelect'); // If you have another dropdown

                        if (configDropdown) {
                            configDropdown.innerHTML = ''; // Clear existing options

                            data.configs.forEach(config => {
                                const option = document.createElement('option');
                                option.value = config;
                                option.textContent = config; // Assuming the config name is also the file name without extension
                                configDropdown.appendChild(option);
                            });

                            if (data.configs.length > 0) {
                                configDropdown.value = data.configs[0]; // Select the first config by default
                            }
                        }

                        // If you have another dropdown to populate, ensure to do the same
                        if (configSelect) {
                            configSelect.innerHTML = ''; // Clear existing options

                            data.configs.forEach(config => {
                                const option = document.createElement('option');
                                option.value = config;
                                option.textContent = config;
                                configSelect.appendChild(option);
                            });

                            if (data.configs.length > 0) {
                                configSelect.value = data.configs[0]; // Select the first config by default
                            }
                        }

                    })
                    .catch(error => {
                        console.error('Error loading configs:', error);
                        // Consider showing a user-friendly message in the UI
                    });
            }

            function fetchWorkerThreads() {
                fetch('http://localhost:8999/get_worker_threads', {
                    headers: {
                        'Authorization': `Bearer ${authToken}` // Add the token here
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        const threadsTableBody = document.querySelector('#threadsTable tbody');
                        threadsTableBody.innerHTML = '';
                        data.forEach(thread => {
                            const row = document.createElement('tr');
                            const pandaLabel = thread.panda_number ? `${thread.panda_number} | ` : '';
                            row.innerHTML = `
                                <td>${pandaLabel}${thread.UDID}</td>
                                <td>${thread.app || 'Spotify'}</td>
                                <td>${thread.status}</td>
                                <td>${thread.streams}</td>
                                <td>${thread.likes}</td>
                                <td>${thread.follows}</td>
                                <td>${thread.errors}</td>
                                <td>${thread.session_time}</td>
                            `;

                            threadsTableBody.appendChild(row);
                        });
                    })
                    .catch(error => {
                        console.error('Error:', error);
                    });
            }

            async function fetchWorkerStats() {
                try {
                    const response = await fetch('http://localhost:8999/get_worker_stats', {
                        headers: {
                            'Authorization': `Bearer ${authToken}` // Add the token here
                        }
                    });
                    const stats = await response.json();

                    document.getElementById('devicesConnected').innerText = stats.worker_devices_connected;
                    document.getElementById('streamsDone').innerText = stats.worker_streams_done;
                    document.getElementById('streamsDoneSpotify').innerText = stats.worker_streams_done_spotify || 0;
                    document.getElementById('streamsDoneTidal').innerText = stats.worker_streams_done_tidal || 0;
                    document.getElementById('streamsDoneApple').innerText = stats.worker_streams_done_apple || 0;
                    document.getElementById('successfulLogins').innerText = stats.worker_successful_logins;
                    document.getElementById('failedLogins').innerText = stats.worker_unsuccessful_logins;
                    document.getElementById('songLikesDone').innerText = stats.worker_song_likes;
                    document.getElementById('albumLikesDone').innerText = stats.worker_album_likes;
                    document.getElementById('followsDone').innerText = stats.worker_follows_done;
                    document.getElementById('proxyErrors').innerText = stats.worker_proxy_errors;
                    document.getElementById('botErrors').innerText = stats.worker_bot_errors;
                } catch (error) {
                    console.error('Error fetching worker stats:', error);
                }
            }

            async function fetchDashboard() {
                try {
                    const response = await fetch('http://localhost:8999/get_dashboard', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    const data = await response.json();
                    const el = document.getElementById('dashboardApps');
                    const statusEl = document.getElementById('dashBotStatus');
                    if (!el) return;
                    statusEl.textContent = data.bot_running ? 'Running' : 'Stopped';
                    statusEl.style.color = data.bot_running ? '#1DB954' : '#ef4444';

                    const devStreamsEl = document.getElementById('dashStreamsInfo');
                    if (devStreamsEl) {
                        devStreamsEl.textContent = `Done: ${data.streams_done || 0} / ${data.streams_target || '?'}  |  Spotify: ${data.streams_spotify || 0}  |  Tidal: ${data.streams_tidal || 0}  |  Apple: ${data.streams_apple || 0}`;
                    }

                    let html = '';
                    for (const dev of data.devices) {
                        const devApps = data.apps.filter(a => a.udid === dev.udid);
                        let appsHtml = '';
                        for (const app of devApps) {
                            const sc = app.state === 'PLAYING' ? 'playing' : (app.state === 'PAUSED' || app.state === 'BUFFERING' || app.state === 'unknown' ? 'paused' : 'stopped');
                            const stColor = app.state === 'PLAYING' ? '#1DB954' : (app.state === 'PAUSED' || app.state === 'BUFFERING' || app.state === 'unknown' ? '#f59e0b' : '#ef4444');
                            const song = app.title ? `${app.title} — ${app.artist}` : 'No song';
                            appsHtml += `<div class="dash-app-row">
                                <div class="dash-app-dot ${sc}"></div>
                                <div class="dash-app-name">${app.app}</div>
                                <div class="dash-app-song">${song}</div>
                                <div class="dash-app-state" style="color:${stColor}">${app.state}</div>
                            </div>`;
                        }
                        const mins = dev.session_time ? Math.round(dev.session_time / 60) : 0;
                        const pandaLabel = dev.panda_number ? `${dev.panda_number}` : dev.udid;
                        html += `<div class="dash-app-card">
                            <div class="dash-device-header">
                                <div class="dash-device-name">${pandaLabel} <span class="dash-device-udid">${dev.udid}</span></div>
                                <div class="dash-device-udid">Streams: <span>${dev.streams || 0}</span> | Errors: <span>${dev.errors || 0}</span> | Up: <span>${mins}m</span></div>
                            </div>
                            ${appsHtml}
                        </div>`;
                    }
                    el.innerHTML = html;
                } catch (error) {
                    console.error('Dashboard fetch error:', error);
                }
            }

            function toggleStartStopButton() {
                const button = document.getElementById('startStopButton');
                if (button.textContent === 'Start') {
                    button.textContent = 'Stop';
                    button.classList.remove('start-button');
                    button.classList.add('stop-button');
                } else {
                    button.textContent = 'Start';
                    button.classList.remove('stop-button');
                    button.classList.add('start-button');
                }
            }

            function toggleWebhook(checkbox) {
                const webhookSection = document.getElementById('webhook-section');
                if (checkbox.checked) {
                    webhookSection.style.display = 'block';
                } else {
                    webhookSection.style.display = 'none';
                }
            }


            function toggleProxies(checkbox) {
                const proxiesSection = document.getElementById('proxies-section');
                if (checkbox.checked) {
                    proxiesSection.style.display = 'block';
                } else {
                    proxiesSection.style.display = 'none';
                }
            }

            function togglePlaytimeInput(select) {
                const playtimeSecondsGroup = document.getElementById('playtime-seconds-group');
                const playtimePercentageGroup = document.getElementById('playtime-percentage-group');
                if (select.value === 'seconds') {
                    playtimeSecondsGroup.style.display = 'block';
                    playtimePercentageGroup.style.display = 'none';
                } else {
                    playtimeSecondsGroup.style.display = 'none';
                    playtimePercentageGroup.style.display = 'block';
                }
            }

            function startTimer() {
                startTime = new Date();
                timerInterval = setInterval(updateTimeRunning, 1000);
            }

            function updateTimeRunning() {
                const now = new Date();
                const elapsedTime = now - startTime;
                const seconds = Math.floor((elapsedTime / 1000) % 60);
                const minutes = Math.floor((elapsedTime / 1000 / 60) % 60);
                const hours = Math.floor((elapsedTime / 1000 / 60 / 60) % 24);
                document.getElementById('timeRunning').textContent =
                    `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            }

            function loadBatches(targetType, targetListId) {
                const listId = targetListId || 'batch-list';
                let batchType = targetType;
                if (!batchType) {
                    if (listId === 'batch-list-tidal') batchType = document.getElementById('batch-type-tidal').value;
                    else if (listId === 'batch-list-apple') batchType = document.getElementById('batch-type-apple').value;
                    else batchType = document.getElementById('batch-type').value;
                }
                const batchList = document.getElementById(listId);
                if (!batchList) return;
                batchList.innerHTML = '';

                fetch(`http://localhost:8999/get_batches?type=${batchType}`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                })
                    .then(response => {
                        if (!response.ok) throw new Error(`Failed to load batches: ${response.statusText}`);
                        return response.json();
                    })
                    .then(data => {
                        if (!data.batches || !Array.isArray(data.batches)) throw new Error('Invalid data format');
                        if (data.batches.length === 0) {
                            const emptyMsg = document.createElement('div');
                            emptyMsg.style.cssText = 'color:#666;text-align:center;padding:10px;font-size:12px;';
                            emptyMsg.textContent = 'No batches found';
                            batchList.appendChild(emptyMsg);
                            return;
                        }
                        data.batches.forEach(batch => {
                            const batchCard = document.createElement('div');
                            batchCard.className = 'batch-card';
                            const inputElement = document.createElement('input');
                            inputElement.type = 'text';
                            inputElement.value = batch.name;
                            inputElement.readOnly = true;
                            const buttonGroup = document.createElement('div');
                            buttonGroup.className = 'button-group';
                            const editButton = document.createElement('button');
                            editButton.className = 'edit-button';
                            editButton.textContent = 'Edit';
                            editButton.addEventListener('click', () => editBatch(batch.type, batch.id, batch.name, batch.content));
                            const deleteButton = document.createElement('button');
                            deleteButton.className = 'delete-button';
                            deleteButton.textContent = 'Delete';
                            deleteButton.addEventListener('click', () => deleteBatch(batch.type, batch.id, listId));
                            buttonGroup.appendChild(editButton);
                            buttonGroup.appendChild(deleteButton);
                            batchCard.appendChild(inputElement);
                            batchCard.appendChild(buttonGroup);
                            batchList.appendChild(batchCard);
                        });
                    })
                    .catch(error => {
                        console.error('Error loading batches:', error);
                        const errMsg = document.createElement('div');
                        errMsg.style.cssText = 'color:#dc3545;text-align:center;padding:10px;font-size:12px;';
                        errMsg.textContent = 'Error loading batches: ' + error.message;
                        batchList.appendChild(errMsg);
                    });
            }

            function deleteBatch(batchType, batchId, reloadListId) {
                fetch(`http://localhost:8999/delete_batch`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ type: batchType, id: batchId })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.message) {
                            const listId = reloadListId || 'batch-list';
                            const typeEl = listId === 'batch-list-tidal' ? 'batch-type-tidal' :
                                           listId === 'batch-list-apple' ? 'batch-type-apple' : 'batch-type';
                            loadBatches(document.getElementById(typeEl).value, listId);
                        }
                    })
                    .catch(error => console.error('Error:', error));
            }

            let currentBatchTarget = { type: 'batch-type', listId: 'batch-list' };

            function showAddBatchModal(targetType, targetListId) {
                currentBatchTarget = { type: targetType || 'batch-type', listId: targetListId || 'batch-list' };
                document.getElementById('batchModalTitle').textContent = 'Add New Batch';
                document.getElementById('batch-name').value = '';
                document.getElementById('batch-content').value = '';
                document.getElementById('batch-file').value = '';
                document.getElementById('batchModalSaveButton').setAttribute('data-edit-mode', 'false');
                document.getElementById('batchModal').style.display = "block";
            }

            function closeAddBatchModal() {
                document.getElementById('batch-name').value = '';
                document.getElementById('batch-content').value = '';
                document.getElementById('batch-file').value = '';
                document.getElementById('batchModal').style.display = "none";
            }

            function reloadBatchOptions() {
                loadBatchOptions('accounts-select', 'accounts');
                loadBatchOptions('proxies-select', 'proxies');
                loadBatchOptions('links-select', 'links');
                loadBatchOptions('tidal-links-select', 'tidal_links');
                loadBatchOptions('apple-links-select', 'apple_links');
            }

            function saveNewBatch() {
                const batchType = document.getElementById(currentBatchTarget.type).value;
                const batchName = document.getElementById('batch-name').value;
                let batchContent = document.getElementById('batch-content').value;
                batchContent = batchContent.split('\n').map(line => line.trim()).filter(line => line.length > 0).join('\n');
                const editMode = document.getElementById('batchModalSaveButton').getAttribute('data-edit-mode') === 'true';

                if (editMode) {
                    const batchId = document.getElementById('batchModalSaveButton').getAttribute('data-batch-id');
                    fetch(`http://localhost:8999/update_batch`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                        body: JSON.stringify({ type: batchType, id: batchId, name: batchName, content: batchContent })
                    })
                        .then(response => response.json())
                        .then(data => {
                            closeAddBatchModal();
                            loadBatches(document.getElementById(currentBatchTarget.type).value, currentBatchTarget.listId);
                            reloadBatchOptions();
                        })
                        .catch(error => console.error('Error updating batch:', error));
                } else {
                    fetch(`http://localhost:8999/add_batch`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                        body: JSON.stringify({ type: batchType, name: batchName, content: batchContent })
                    })
                        .then(response => response.json())
                        .then(data => {
                            closeAddBatchModal();
                            loadBatches(document.getElementById(currentBatchTarget.type).value, currentBatchTarget.listId);
                            reloadBatchOptions();
                        })
                        .catch(error => console.error('Error adding batch:', error));
                }
            }

            function editBatch(batchType, batchId, batchName, batchContent) {
                document.getElementById('batchModalTitle').textContent = 'Edit Batch';
                document.getElementById('batch-name').value = batchName;
                document.getElementById('batch-content').value = batchContent;
                document.getElementById('batchModalSaveButton').setAttribute('data-edit-mode', 'true');
                document.getElementById('batchModalSaveButton').setAttribute('data-batch-id', batchId);
                document.getElementById('batchModal').style.display = "block";
            }

            document.getElementById('batch-file').addEventListener('change', function (event) {
                const file = event.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function (e) {
                        document.getElementById('batch-content').value = e.target.result;
                    };
                    reader.readAsText(file);
                }
            });

            const ctx = document.getElementById('streamsChart').getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, 'rgba(255, 255, 255, 0.5)');
            gradient.addColorStop(1, 'rgba(0, 0, 0, 0.5)');

            const streamsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Streams Done',
                        data: [],
                        fill: true,
                        backgroundColor: gradient,
                        borderColor: 'rgba(255, 255, 255, 1)',
                        tension: 0.1
                    }]
                },
                options: {
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'day',
                                tooltipFormat: 'DD/MM/YYYY',
                                displayFormats: {
                                    day: 'DD/MM/YYYY'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Streams Done'
                            }
                        }
                    }
                }
            });

            function saveCurrentSettings() {
                const settingsData = {
                    apiKey: document.getElementById('api-key').value,
                    // Add other settings here as needed
                };

                fetch('http://localhost:8999/save_settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}` // Add the token here
                    },
                    body: JSON.stringify(settingsData)
                })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Settings saved automatically:', data.message);
                    })
                    .catch(error => {
                        console.error('Error auto-saving settings:', error);
                    });
            }

            // Function to load settings when the settings tab is opened
            function loadSettings() {
                fetch('http://localhost:8999/load_settings', {
                    headers: {
                        'Authorization': `Bearer ${authToken}` // Add the token here
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('api-key').value = data.apiKey;
                        // Load other settings as needed
                    })
                    .catch(error => {
                        console.error('Error loading settings:', error);
                    });
            }

            function updateChart() {
                const startDate = document.getElementById('startDate').value;
                const endDate = document.getElementById('endDate').value;

                fetch(`http://localhost:8999/get_streams_done?start_date=${startDate}&end_date=${endDate}`, {
                    headers: {
                        'Authorization': `Bearer ${authToken}` // Add the token here
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            alert(data.error);
                            return;
                        }

                        const testData = data.streams;

                        // Create a map to store the streams done per day
                        const streamsPerDay = {};

                        testData.forEach(item => {
                            const date = item.timestamp.split(' ')[0]; // Get only the date part
                            if (!streamsPerDay[date]) {
                                streamsPerDay[date] = 0;
                            }
                            streamsPerDay[date] += item.streams_done;
                        });

                        // Generate the full range of dates between startDate and endDate
                        const dateRange = [];
                        let currentDate = new Date(startDate);
                        const end = new Date(endDate);
                        while (currentDate <= end) {
                            const formattedDate = currentDate.toISOString().split('T')[0];
                            dateRange.push(formattedDate);
                            if (!streamsPerDay[formattedDate]) {
                                streamsPerDay[formattedDate] = 0; // Fill missing dates with 0 streams
                            }
                            currentDate.setDate(currentDate.getDate() + 1);
                        }

                        const labels = dateRange;
                        const streamsData = dateRange.map(date => streamsPerDay[date]);

                        streamsChart.data.labels = labels;
                        streamsChart.data.datasets[0].data = streamsData;
                        streamsChart.update();

                        const totalStreams = streamsData.reduce((acc, streams) => acc + streams, 0);
                        document.getElementById('totalStreamsText').innerText = `Total Streams Done: ${totalStreams}`;
                    })
                    .catch(error => {
                        console.error('Error fetching streams data:', error);
                    });
            }

            document.getElementById('startDate').addEventListener('change', updateChart);
            document.getElementById('endDate').addEventListener('change', updateChart);

        });
    }

    function hideLoadingModal() {
        const loadingModal = document.getElementById('loadingModal');
        const mainContent = document.getElementById('main-content');

        if (loadingModal) {
            loadingModal.style.display = 'none';
        }

        if (mainContent) {
            mainContent.classList.remove('blurred');
        }
    }
});