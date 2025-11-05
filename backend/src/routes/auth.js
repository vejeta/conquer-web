// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const db = require('../database');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-this';
const JWT_EXPIRY = '24h';

// Register new user
router.post('/register', async (req, res) => {
    try {
        const { username, email, password } = req.body;

        // Validation
        if (!username || !email || !password) {
            return res.status(400).json({ message: 'Todos los campos son requeridos' });
        }

        if (username.length < 3 || username.length > 20) {
            return res.status(400).json({ message: 'El usuario debe tener entre 3 y 20 caracteres' });
        }

        if (password.length < 8) {
            return res.status(400).json({ message: 'La contraseña debe tener al menos 8 caracteres' });
        }

        // Check if user exists
        const existingUser = db.prepare('SELECT id FROM users WHERE username = ? OR email = ?').get(username, email);
        if (existingUser) {
            return res.status(409).json({ message: 'El usuario o email ya existe' });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Insert user
        const result = db.prepare(`
            INSERT INTO users (username, email, password)
            VALUES (?, ?, ?)
        `).run(username, email, hashedPassword);

        res.status(201).json({
            message: 'Usuario registrado exitosamente',
            userId: result.lastInsertRowid
        });
    } catch (error) {
        console.error('Registration error:', error);
        res.status(500).json({ message: 'Error al registrar usuario' });
    }
});

// Login
router.post('/login', async (req, res) => {
    try {
        const { username, password, remember } = req.body;

        // Validation
        if (!username || !password) {
            return res.status(400).json({ message: 'Usuario y contraseña son requeridos' });
        }

        // Get user
        const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username);

        if (!user) {
            return res.status(401).json({ message: 'Usuario o contraseña incorrectos' });
        }

        if (!user.active) {
            return res.status(403).json({ message: 'Usuario desactivado' });
        }

        // Verify password
        const validPassword = await bcrypt.compare(password, user.password);

        if (!validPassword) {
            return res.status(401).json({ message: 'Usuario o contraseña incorrectos' });
        }

        // Update last login
        db.prepare('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?').run(user.id);

        // Generate JWT token
        const token = jwt.sign(
            { userId: user.id, username: user.username, role: user.role },
            JWT_SECRET,
            { expiresIn: remember ? '7d' : JWT_EXPIRY }
        );

        // Store session
        const expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + (remember ? 168 : 24));

        db.prepare(`
            INSERT INTO sessions (user_id, token, ip, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?)
        `).run(user.id, token, req.ip, req.get('user-agent'), expiresAt.toISOString());

        res.json({
            token,
            user: {
                id: user.id,
                username: user.username,
                email: user.email,
                role: user.role
            }
        });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ message: 'Error al iniciar sesión' });
    }
});

// Verify token
router.get('/verify', (req, res) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ message: 'Token no proporcionado' });
        }

        const token = authHeader.substring(7);

        // Verify JWT
        const decoded = jwt.verify(token, JWT_SECRET);

        // Check if session exists and is valid
        const session = db.prepare(`
            SELECT s.*, u.username, u.email, u.role, u.active
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP
        `).get(token);

        if (!session || !session.active) {
            return res.status(401).json({ message: 'Sesión inválida' });
        }

        res.json({
            user: {
                id: session.user_id,
                username: session.username,
                email: session.email,
                role: session.role
            }
        });
    } catch (error) {
        if (error.name === 'JsonWebTokenError' || error.name === 'TokenExpiredError') {
            return res.status(401).json({ message: 'Token inválido o expirado' });
        }
        console.error('Verification error:', error);
        res.status(500).json({ message: 'Error al verificar token' });
    }
});

// Refresh token
router.post('/refresh', (req, res) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ message: 'Token no proporcionado' });
        }

        const oldToken = authHeader.substring(7);

        // Verify old token (even if expired)
        const decoded = jwt.verify(oldToken, JWT_SECRET, { ignoreExpiration: true });

        // Generate new token
        const newToken = jwt.sign(
            { userId: decoded.userId, username: decoded.username, role: decoded.role },
            JWT_SECRET,
            { expiresIn: JWT_EXPIRY }
        );

        // Update session
        const expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + 24);

        db.prepare(`
            UPDATE sessions
            SET token = ?, expires_at = ?
            WHERE token = ?
        `).run(newToken, expiresAt.toISOString(), oldToken);

        res.json({ token: newToken });
    } catch (error) {
        console.error('Refresh error:', error);
        res.status(401).json({ message: 'Error al refrescar token' });
    }
});

// Logout
router.post('/logout', (req, res) => {
    try {
        const authHeader = req.headers.authorization;

        if (authHeader && authHeader.startsWith('Bearer ')) {
            const token = authHeader.substring(7);

            // Delete session
            db.prepare('DELETE FROM sessions WHERE token = ?').run(token);
        }

        res.json({ message: 'Sesión cerrada exitosamente' });
    } catch (error) {
        console.error('Logout error:', error);
        res.status(500).json({ message: 'Error al cerrar sesión' });
    }
});

// Password recovery (placeholder)
router.post('/password-recovery', async (req, res) => {
    try {
        const { email } = req.body;

        // In production, send actual email
        // For now, just return success
        console.log(`Password recovery requested for: ${email}`);

        res.json({ message: 'Si el email existe, recibirás instrucciones para recuperar tu contraseña' });
    } catch (error) {
        console.error('Password recovery error:', error);
        res.status(500).json({ message: 'Error al procesar solicitud' });
    }
});

module.exports = router;
