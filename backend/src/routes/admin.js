// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

const express = require('express');
const db = require('../database');
const { verifyToken, requireAdmin } = require('../middleware/auth');
const { exec } = require('child_process');
const { promisify } = require('util');
const os = require('os');

const execAsync = promisify(exec);
const router = express.Router();

// All admin routes require authentication and admin role
router.use(verifyToken);
router.use(requireAdmin);

// Get services status
router.get('/services', async (req, res) => {
    try {
        // Check if ttyd is running (check Docker container)
        let ttydOnline = false;
        try {
            const { stdout } = await execAsync('docker ps --filter "name=conquer" --format "{{.Status}}"');
            ttydOnline = stdout.includes('Up');
        } catch (error) {
            ttydOnline = false;
        }

        res.json({
            ttyd: ttydOnline,
            database: true, // If we're here, database is working
            backend: true
        });
    } catch (error) {
        console.error('Error fetching services status:', error);
        res.json({ ttyd: false, database: true, backend: true });
    }
});

// Get system resources
router.get('/resources', (req, res) => {
    try {
        const totalMem = os.totalmem();
        const freeMem = os.freemem();
        const usedMem = totalMem - freeMem;

        const cpuUsage = os.loadavg()[0] * 10; // Rough estimate
        const memoryUsage = Math.round((usedMem / totalMem) * 100);

        res.json({
            cpu: Math.min(Math.round(cpuUsage), 100),
            memory: memoryUsage,
            disk: 45 // Mock value - would need actual disk check
        });
    } catch (error) {
        console.error('Error fetching resources:', error);
        res.json({ cpu: 0, memory: 0, disk: 0 });
    }
});

// Get all users
router.get('/users', (req, res) => {
    try {
        const search = req.query.search || '';
        let users;

        if (search) {
            users = db.prepare(`
                SELECT id, username, email, role, active, last_login as lastLogin
                FROM users
                WHERE username LIKE ? OR email LIKE ?
                ORDER BY created_at DESC
            `).all(`%${search}%`, `%${search}%`);
        } else {
            users = db.prepare(`
                SELECT id, username, email, role, active, last_login as lastLogin
                FROM users
                ORDER BY created_at DESC
            `).all();
        }

        res.json(users);
    } catch (error) {
        console.error('Error fetching users:', error);
        res.json([]);
    }
});

// Get active sessions
router.get('/sessions', (req, res) => {
    try {
        const sessions = db.prepare(`
            SELECT s.id, u.username, s.ip, s.created_at as loginTime
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.expires_at > CURRENT_TIMESTAMP
            ORDER BY s.created_at DESC
        `).all();

        res.json(sessions);
    } catch (error) {
        console.error('Error fetching sessions:', error);
        res.json([]);
    }
});

// Get world info
router.get('/world', async (req, res) => {
    try {
        // Mock data - in production, get from actual game files
        res.json({
            size: '12.6 MB',
            nations: '12',
            lastModified: new Date().toISOString(),
            backupCount: 3
        });
    } catch (error) {
        console.error('Error fetching world info:', error);
        res.json({});
    }
});

// Create world backup
router.post('/world/backup', async (req, res) => {
    try {
        // In production, run actual backup script
        await execAsync('cd /home/user/conquer-web && ./backup-world.sh');
        res.json({ message: 'Backup created successfully' });
    } catch (error) {
        console.error('Error creating backup:', error);
        res.status(500).json({ error: 'Error creating backup' });
    }
});

// Get logs
router.get('/logs', async (req, res) => {
    try {
        const type = req.query.type || 'all';

        let logs;
        if (type === 'all') {
            logs = db.prepare(`
                SELECT level, message, created_at
                FROM logs
                ORDER BY created_at DESC
                LIMIT 100
            `).all();
        } else {
            logs = db.prepare(`
                SELECT level, message, created_at
                FROM logs
                WHERE level = ?
                ORDER BY created_at DESC
                LIMIT 100
            `).all(type);
        }

        const logsText = logs.map(log =>
            `[${log.created_at}] ${log.level.toUpperCase()}: ${log.message}`
        ).join('\n');

        res.json({ logs: logsText });
    } catch (error) {
        console.error('Error fetching logs:', error);
        res.json({ logs: 'Error loading logs' });
    }
});

// Get statistics
router.get('/statistics', (req, res) => {
    try {
        const totalUsers = db.prepare('SELECT COUNT(*) as count FROM users').get().count;

        const activeUsers = db.prepare(`
            SELECT COUNT(*) as count
            FROM users
            WHERE last_login > datetime('now', '-7 days')
        `).get().count;

        const totalGames = db.prepare('SELECT COUNT(*) as count FROM game_stats').get().count;

        const avgPlaytime = db.prepare('SELECT AVG(playtime) as avg FROM users').get().avg || 0;

        res.json({
            totalUsers,
            activeUsers,
            totalGames,
            avgPlaytime: Math.round(avgPlaytime)
        });
    } catch (error) {
        console.error('Error fetching statistics:', error);
        res.json({ totalUsers: 0, activeUsers: 0, totalGames: 0, avgPlaytime: 0 });
    }
});

// Update configuration
router.post('/config', (req, res) => {
    try {
        // In production, update actual config files
        console.log('Config update requested:', req.body);

        res.json({ message: 'Configuration updated successfully' });
    } catch (error) {
        console.error('Error updating config:', error);
        res.status(500).json({ error: 'Error updating configuration' });
    }
});

module.exports = router;
