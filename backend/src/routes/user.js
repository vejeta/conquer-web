// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

const express = require('express');
const db = require('../database');
const { verifyToken } = require('../middleware/auth');

const router = express.Router();

// Get user stats
router.get('/stats', verifyToken, (req, res) => {
    try {
        const user = db.prepare(`
            SELECT score, battles, cities, playtime
            FROM users
            WHERE id = ?
        `).get(req.userId);

        res.json(user || { score: 0, battles: 0, cities: 0, playtime: 0 });
    } catch (error) {
        console.error('Error fetching user stats:', error);
        res.status(500).json({ error: 'Error al obtener estadísticas' });
    }
});

module.exports = router;
