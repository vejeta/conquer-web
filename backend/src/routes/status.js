// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

const express = require('express');
const db = require('../database');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);
const router = express.Router();

// Get server status
router.get('/status', async (req, res) => {
    try {
        // Count active sessions
        const result = db.prepare(`
            SELECT COUNT(*) as count
            FROM sessions
            WHERE expires_at > CURRENT_TIMESTAMP
        `).get();

        const playersOnline = result.count || 0;
        const maxClients = parseInt(process.env.MAX_CLIENTS) || 5;

        res.json({
            online: true,
            playersOnline,
            maxClients
        });
    } catch (error) {
        console.error('Error fetching status:', error);
        res.json({ online: false, playersOnline: 0, maxClients: 5 });
    }
});

// Get players online
router.get('/players/online', (req, res) => {
    try {
        const players = db.prepare(`
            SELECT u.username, s.created_at as loginTime
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.expires_at > CURRENT_TIMESTAMP
            ORDER BY s.created_at DESC
        `).all();

        res.json(players);
    } catch (error) {
        console.error('Error fetching online players:', error);
        res.json([]);
    }
});

// Get world stats
router.get('/world/stats', (req, res) => {
    try {
        // Mock data - in production, read from game files
        res.json({
            nations: '12',
            cities: '45',
            wars: '3',
            size: '12.6 MB'
        });
    } catch (error) {
        console.error('Error fetching world stats:', error);
        res.json({});
    }
});

// Get ranking
router.get('/ranking', (req, res) => {
    try {
        const ranking = db.prepare(`
            SELECT username, score
            FROM users
            WHERE role = 'player' AND score > 0
            ORDER BY score DESC
            LIMIT 10
        `).all();

        res.json(ranking);
    } catch (error) {
        console.error('Error fetching ranking:', error);
        res.json([]);
    }
});

// Get news
router.get('/news', (req, res) => {
    try {
        const news = db.prepare(`
            SELECT text, created_at as date
            FROM news
            ORDER BY created_at DESC
            LIMIT 10
        `).all();

        res.json(news);
    } catch (error) {
        console.error('Error fetching news:', error);
        res.json([]);
    }
});

module.exports = router;
