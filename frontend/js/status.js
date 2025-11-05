// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

// API Configuration
const API_BASE = '/api';

// Fetch server status
async function fetchServerStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();

        // Update server status
        const serverStatus = document.getElementById('server-status');
        if (serverStatus) {
            if (data.online) {
                serverStatus.innerHTML = '<span class="status-indicator"></span>En línea';
                serverStatus.classList.add('online');
            } else {
                serverStatus.innerHTML = 'Fuera de línea';
                serverStatus.classList.remove('online');
            }
        }

        // Update players online
        const playersOnline = document.getElementById('players-online');
        if (playersOnline) {
            playersOnline.textContent = data.playersOnline || '0';
        }

        // Update slots available
        const slotsAvailable = document.getElementById('slots-available');
        if (slotsAvailable) {
            const available = (data.maxClients || 5) - (data.playersOnline || 0);
            slotsAvailable.textContent = available >= 0 ? available : '0';
        }
    } catch (error) {
        console.error('Error fetching server status:', error);
        const serverStatus = document.getElementById('server-status');
        if (serverStatus) {
            serverStatus.innerHTML = 'Error';
            serverStatus.classList.remove('online');
        }
    }
}

// Initial fetch
fetchServerStatus();

// Refresh status every 10 seconds
setInterval(fetchServerStatus, 10000);
