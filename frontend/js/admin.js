// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

// API Configuration
const API_BASE = '/api';

// Get auth token
function getAuthToken() {
    return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
}

// Check admin authentication
async function checkAdminAuth() {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/login.html';
        return false;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            window.location.href = '/login.html';
            return false;
        }

        const data = await response.json();

        // Check if user is admin
        if (data.user.role !== 'admin') {
            alert('Acceso denegado. Solo administradores pueden acceder a esta página.');
            window.location.href = '/dashboard.html';
            return false;
        }

        return true;
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
        return false;
    }
}

// Load service status
async function loadServiceStatus() {
    try {
        const response = await fetch(`${API_BASE}/admin/services`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const data = await response.json();

            document.getElementById('ttyd-status').textContent = data.ttyd ? 'Online' : 'Offline';
            document.getElementById('ttyd-status').classList.toggle('online', data.ttyd);

            document.getElementById('db-status').textContent = data.database ? 'Online' : 'Offline';
            document.getElementById('db-status').classList.toggle('online', data.database);
        }
    } catch (error) {
        console.error('Error loading service status:', error);
    }
}

// Load system resources
async function loadSystemResources() {
    try {
        const response = await fetch(`${API_BASE}/admin/resources`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const data = await response.json();

            // Update CPU
            document.getElementById('cpu-usage').style.width = `${data.cpu}%`;
            document.getElementById('cpu-value').textContent = `${data.cpu}%`;

            // Update Memory
            document.getElementById('memory-usage').style.width = `${data.memory}%`;
            document.getElementById('memory-value').textContent = `${data.memory}%`;

            // Update Disk
            document.getElementById('disk-usage').style.width = `${data.disk}%`;
            document.getElementById('disk-value').textContent = `${data.disk}%`;

            // Color code based on usage
            updateResourceColor('cpu-usage', data.cpu);
            updateResourceColor('memory-usage', data.memory);
            updateResourceColor('disk-usage', data.disk);
        }
    } catch (error) {
        console.error('Error loading system resources:', error);
    }
}

function updateResourceColor(elementId, usage) {
    const element = document.getElementById(elementId);
    if (usage >= 90) {
        element.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
    } else if (usage >= 70) {
        element.style.background = 'linear-gradient(90deg, #f59e0b, #d97706)';
    } else {
        element.style.background = 'linear-gradient(90deg, var(--primary-color), var(--primary-hover))';
    }
}

// Load users table
async function loadUsers(search = '') {
    try {
        const url = search
            ? `${API_BASE}/admin/users?search=${encodeURIComponent(search)}`
            : `${API_BASE}/admin/users`;

        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const users = await response.json();
            const tbody = document.getElementById('users-table');

            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="loading">No se encontraron usuarios</td></tr>';
                return;
            }

            tbody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.username}</td>
                    <td>${user.email}</td>
                    <td><span class="badge">${user.role}</span></td>
                    <td>${user.active ? '<span class="status-badge online">Activo</span>' : 'Inactivo'}</td>
                    <td>${user.lastLogin ? new Date(user.lastLogin).toLocaleString() : 'Nunca'}</td>
                    <td>
                        <button class="btn btn-small btn-secondary" onclick="editUser('${user.id}')">Editar</button>
                        <button class="btn btn-small btn-danger" onclick="deleteUser('${user.id}')">Eliminar</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

// Load active sessions
async function loadActiveSessions() {
    try {
        const response = await fetch(`${API_BASE}/admin/sessions`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const sessions = await response.json();
            const tbody = document.getElementById('sessions-table');
            const count = document.getElementById('active-sessions-count');

            count.textContent = sessions.length;

            if (sessions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="loading">No hay sesiones activas</td></tr>';
                return;
            }

            tbody.innerHTML = sessions.map(session => `
                <tr>
                    <td>${session.username}</td>
                    <td>${session.ip}</td>
                    <td>${new Date(session.loginTime).toLocaleString()}</td>
                    <td>${session.activity || 'Inactivo'}</td>
                    <td>
                        <button class="btn btn-small btn-danger" onclick="killSession('${session.id}')">Cerrar</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

// Load world info
async function loadWorldInfo() {
    try {
        const response = await fetch(`${API_BASE}/admin/world`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const data = await response.json();

            document.getElementById('world-data-size').textContent = data.size || 'N/A';
            document.getElementById('world-nations-count').textContent = data.nations || 'N/A';
            document.getElementById('world-last-modified').textContent = data.lastModified
                ? new Date(data.lastModified).toLocaleString()
                : 'N/A';
            document.getElementById('backup-count').textContent = data.backupCount || '0';
        }
    } catch (error) {
        console.error('Error loading world info:', error);
    }
}

// Load logs
async function loadLogs(type = 'all') {
    try {
        const response = await fetch(`${API_BASE}/admin/logs?type=${type}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            const logsOutput = document.querySelector('.logs-output');
            logsOutput.textContent = data.logs || 'No hay logs disponibles';
        }
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/admin/statistics`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const stats = await response.json();

            document.getElementById('total-users').textContent = stats.totalUsers || '0';
            document.getElementById('active-users').textContent = stats.activeUsers || '0';
            document.getElementById('total-games').textContent = stats.totalGames || '0';
            document.getElementById('avg-playtime').textContent = `${stats.avgPlaytime || 0}h`;
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Backup world
async function backupWorld() {
    if (!confirm('¿Estás seguro de que deseas crear un backup del mundo?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/world/backup`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            alert('Backup creado exitosamente');
            loadWorldInfo();
        } else {
            alert('Error al crear el backup');
        }
    } catch (error) {
        console.error('Error creating backup:', error);
        alert('Error al crear el backup');
    }
}

// Event listeners
document.getElementById('logout-btn')?.addEventListener('click', () => {
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_token');
    window.location.href = '/index.html';
});

document.getElementById('refresh-services')?.addEventListener('click', loadServiceStatus);
document.getElementById('refresh-logs')?.addEventListener('click', () => loadLogs(document.getElementById('log-type').value));

document.getElementById('user-search')?.addEventListener('input', (e) => {
    loadUsers(e.target.value);
});

document.getElementById('log-type')?.addEventListener('change', (e) => {
    loadLogs(e.target.value);
});

document.getElementById('backup-world-btn')?.addEventListener('click', backupWorld);

document.getElementById('download-logs')?.addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_BASE}/admin/logs/download`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `conquer-logs-${Date.now()}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }
    } catch (error) {
        console.error('Error downloading logs:', error);
    }
});

// Config form
document.getElementById('config-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const config = {
        maxClients: document.getElementById('max-clients').value,
        sessionTimeout: document.getElementById('session-timeout').value,
        ttydFontSize: document.getElementById('ttyd-font-size').value,
        maintenanceMode: document.getElementById('maintenance-mode').checked,
        allowRegistration: document.getElementById('allow-registration').checked,
        requireEmailVerification: document.getElementById('require-email-verification').checked
    };

    try {
        const response = await fetch(`${API_BASE}/admin/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            alert('Configuración guardada exitosamente');
        } else {
            alert('Error al guardar la configuración');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        alert('Error al guardar la configuración');
    }
});

// Initialize admin panel
async function init() {
    const isAdmin = await checkAdminAuth();
    if (!isAdmin) return;

    loadServiceStatus();
    loadSystemResources();
    loadUsers();
    loadActiveSessions();
    loadWorldInfo();
    loadLogs();
    loadStatistics();

    // Refresh data periodically
    setInterval(loadServiceStatus, 10000);
    setInterval(loadSystemResources, 5000);
    setInterval(loadActiveSessions, 15000);
}

// Run on page load
init();
