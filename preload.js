const { contextBridge, ipcRenderer } = require('electron');

// Define allowed channels for send and receive to ensure security
const validSendChannels = ['toggle-console', 'toggle-always-on-top', 'minimize-app', 'close-app', 'send-token', 'login-attempt', 'login-success'];
const validReceiveChannels = ['console-toggled', 'token-received', 'login-response', 'ai-progress'];
const validInvokeChannels = ['ai-status', 'ai-chat', 'ai-reset'];

contextBridge.exposeInMainWorld('electronAPI', {
    saveSettings: (settings) => ipcRenderer.send('save-settings', settings),
    loadSettings: () => ipcRenderer.invoke('load-settings'),
    toggleAlwaysOnTop: (isOnTop) => {
        if (validSendChannels.includes('toggle-always-on-top')) {
            ipcRenderer.send('toggle-always-on-top', isOnTop);
        }
    },
    minimizeApp: () => {
        if (validSendChannels.includes('minimize-app')) {
            ipcRenderer.send('minimize-app');
        }
    },
    closeApp: () => {
        if (validSendChannels.includes('close-app')) {
            ipcRenderer.send('close-app');
        }
    },
    sendTokenToRenderer: (token) => {
        if (validSendChannels.includes('send-token')) {
            ipcRenderer.send('send-token', token);
        }
    },
    onTokenReceived: (callback) => {
        if (validReceiveChannels.includes('token-received')) {
            ipcRenderer.on('token-received', (event, token) => callback(token));
        }
    },
    onAiProgress: (callback) => {
        if (validReceiveChannels.includes('ai-progress')) {
            const listener = (event, progress) => callback(progress);
            ipcRenderer.on('ai-progress', listener);
            return () => ipcRenderer.removeListener('ai-progress', listener);
        }
        return null;
    },
    send: (channel, data) => {
        if (validSendChannels.includes(channel)) {
            ipcRenderer.send(channel, data);
        }
    },
    receive: (channel, func) => {
        if (validReceiveChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => func(...args));
        }
    },
    aiStatus: () => {
        if (validInvokeChannels.includes('ai-status')) {
            return ipcRenderer.invoke('ai-status');
        }
        return Promise.resolve({ ready: false, error: 'canal no permitido' });
    },
    aiChat: (payload) => {
        if (validInvokeChannels.includes('ai-chat')) {
            return ipcRenderer.invoke('ai-chat', payload);
        }
        return Promise.resolve({ ok: false, error: 'canal no permitido' });
    },
    aiReset: () => {
        if (validInvokeChannels.includes('ai-reset')) {
            return ipcRenderer.invoke('ai-reset');
        }
        return Promise.resolve({ ok: false, error: 'canal no permitido' });
    }
});
