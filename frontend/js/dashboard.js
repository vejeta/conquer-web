// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

// API Configuration
const API_BASE = '/api';

// Get auth token
function getAuthToken() {
    return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
}

// Check authentication
async function checkAuth() {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/login.html';
        return null;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            // Token invalid, redirect to login
            localStorage.removeItem('auth_token');
            sessionStorage.removeItem('auth_token');
            window.location.href = '/login.html';
            return null;
        }

        const data = await response.json();
        return data.user;
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
        return null;
    }
}

// Load user data
async function loadUserData() {
    const user = await checkAuth();
    if (!user) return;

    // Update username
    document.getElementById('username').textContent = user.username;

    // Load user stats
    try {
        const response = await fetch(`${API_BASE}/user/stats`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const stats = await response.json();

            document.getElementById('user-score').textContent = stats.score || '0';
            document.getElementById('user-battles').textContent = stats.battles || '0';
            document.getElementById('user-cities').textContent = stats.cities || '0';
            document.getElementById('user-playtime').textContent = `${stats.playtime || 0}h`;

            // Show admin link if user is admin
            if (user.role === 'admin') {
                document.getElementById('admin-link').style.display = 'flex';
            }
        }
    } catch (error) {
        console.error('Error loading user stats:', error);
    }
}

// Load server status
async function loadServerStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();

        // Update server status
        const serverStatus = document.getElementById('server-status');
        if (data.online) {
            serverStatus.innerHTML = '<span class="status-dot"></span>En línea';
            serverStatus.classList.add('online');
        } else {
            serverStatus.textContent = 'Fuera de línea';
            serverStatus.classList.remove('online');
        }

        // Update players online
        document.getElementById('players-online').textContent = data.playersOnline || '0';

        // Update slots available
        const available = (data.maxClients || 5) - (data.playersOnline || 0);
        document.getElementById('slots-available').textContent = available >= 0 ? available : '0';

        // Disable play button if no slots
        const playBtn = document.getElementById('play-btn');
        if (available <= 0) {
            playBtn.disabled = true;
            playBtn.textContent = 'Servidor Lleno';
        } else {
            playBtn.disabled = false;
            playBtn.textContent = '🎮 Entrar al Juego';
        }
    } catch (error) {
        console.error('Error loading server status:', error);
    }
}

// Load players online
async function loadPlayersOnline() {
    try {
        const response = await fetch(`${API_BASE}/players/online`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const players = await response.json();
            const playersList = document.getElementById('players-list');

            if (players.length === 0) {
                playersList.innerHTML = '<div class="loading">No hay jugadores conectados</div>';
            } else {
                playersList.innerHTML = players.map(player => `
                    <div class="player-item">
                        <span class="player-name">${player.username}</span>
                        <span class="player-status">Jugando</span>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error loading players:', error);
    }
}

// Load world stats
async function loadWorldStats() {
    try {
        const response = await fetch(`${API_BASE}/world/stats`);
        const data = await response.json();

        document.getElementById('world-nations').textContent = data.nations || 'N/A';
        document.getElementById('world-cities').textContent = data.cities || 'N/A';
        document.getElementById('world-wars').textContent = data.wars || 'N/A';
        document.getElementById('world-size').textContent = data.size || 'N/A';
    } catch (error) {
        console.error('Error loading world stats:', error);
    }
}

// Load ranking
async function loadRanking() {
    try {
        const response = await fetch(`${API_BASE}/ranking`);
        const ranking = await response.json();

        const rankingList = document.getElementById('ranking-list');

        if (ranking.length === 0) {
            rankingList.innerHTML = '<div class="loading">No hay ranking disponible</div>';
        } else {
            rankingList.innerHTML = ranking.slice(0, 5).map((player, index) => `
                <div class="ranking-item">
                    <span class="rank">${index + 1}.</span>
                    <span class="player-name">${player.username}</span>
                    <span class="player-score">${player.score}</span>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading ranking:', error);
    }
}

// Load news
async function loadNews() {
    try {
        const response = await fetch(`${API_BASE}/news`);
        const news = await response.json();

        const newsList = document.getElementById('news-list');

        if (news.length === 0) {
            newsList.innerHTML = '<div class="loading">No hay noticias recientes</div>';
        } else {
            newsList.innerHTML = news.slice(0, 5).map(item => `
                <div class="news-item">
                    <div class="news-date">${new Date(item.date).toLocaleDateString()}</div>
                    <div class="news-text">${item.text}</div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading news:', error);
    }
}

// Session timeout warning
let sessionTimeout;
let warningTimeout;

function setupSessionWarning() {
    const sessionDuration = 30 * 60 * 1000; // 30 minutes
    const warningTime = 5 * 60 * 1000; // 5 minutes before expiry

    // Clear existing timers
    clearTimeout(sessionTimeout);
    clearTimeout(warningTimeout);

    // Set warning timer
    warningTimeout = setTimeout(() => {
        showTimeoutWarning();
    }, sessionDuration - warningTime);

    // Set session timeout
    sessionTimeout = setTimeout(() => {
        handleSessionTimeout();
    }, sessionDuration);
}

function showTimeoutWarning() {
    const modal = document.getElementById('timeout-modal');
    const countdown = document.getElementById('timeout-countdown');
    modal.classList.add('active');

    let timeLeft = 5 * 60; // 5 minutes in seconds
    const countdownInterval = setInterval(() => {
        timeLeft--;
        countdown.textContent = Math.floor(timeLeft / 60);

        if (timeLeft <= 0) {
            clearInterval(countdownInterval);
        }
    }, 1000);
}

function handleSessionTimeout() {
    // Clear tokens
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_token');

    // Redirect to login
    alert('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
    window.location.href = '/login.html';
}

// Extend session
document.getElementById('extend-session-btn')?.addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (response.ok) {
            const data = await response.json();

            // Update token
            if (localStorage.getItem('auth_token')) {
                localStorage.setItem('auth_token', data.token);
            } else {
                sessionStorage.setItem('auth_token', data.token);
            }

            // Close modal
            document.getElementById('timeout-modal').classList.remove('active');

            // Reset timers
            setupSessionWarning();
        }
    } catch (error) {
        console.error('Error extending session:', error);
    }
});

// Logout now
document.getElementById('logout-now-btn')?.addEventListener('click', () => {
    logout();
});

// Logout
function logout() {
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_token');
    window.location.href = '/index.html';
}

document.getElementById('logout-btn')?.addEventListener('click', logout);

// Play button
document.getElementById('play-btn')?.addEventListener('click', async () => {
    const token = getAuthToken();

    // Create a form to send token to ttyd via POST
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/play';
    form.target = '_blank';

    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'token';
    input.value = token;

    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
});

// Initialize dashboard
async function init() {
    await loadUserData();
    loadServerStatus();
    loadPlayersOnline();
    loadWorldStats();
    loadRanking();
    loadNews();
    setupSessionWarning();

    // Refresh data periodically
    setInterval(loadServerStatus, 10000); // Every 10 seconds
    setInterval(loadPlayersOnline, 15000); // Every 15 seconds
    setInterval(loadWorldStats, 30000); // Every 30 seconds
}

// Run on page load
init();
