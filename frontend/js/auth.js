// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

// API Configuration
const API_BASE = '/api';

// DOM Elements
const tabBtns = document.querySelectorAll('.tab-btn');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const loginError = document.getElementById('login-error');
const loginSuccess = document.getElementById('login-success');
const registerError = document.getElementById('register-error');
const registerSuccess = document.getElementById('register-success');
const forgotPasswordLink = document.getElementById('forgot-password');
const passwordModal = document.getElementById('password-modal');
const passwordModalClose = passwordModal?.querySelector('.modal-close');
const passwordRecoveryForm = document.getElementById('password-recovery-form');
const recoveryError = document.getElementById('recovery-error');
const recoverySuccess = document.getElementById('recovery-success');

// Tab Switching
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all tabs and forms
        tabBtns.forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));

        // Add active class to clicked tab
        btn.classList.add('active');

        // Show corresponding form
        const tab = btn.dataset.tab;
        if (tab === 'login') {
            loginForm.classList.add('active');
        } else if (tab === 'register') {
            registerForm.classList.add('active');
        }
    });
});

// Login Form Submission
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const remember = document.getElementById('remember-me').checked;

    // Hide previous messages
    loginError.style.display = 'none';
    loginSuccess.style.display = 'none';

    // Disable submit button
    const submitBtn = loginForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Iniciando sesión...';

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password, remember })
        });

        const data = await response.json();

        if (response.ok) {
            // Store token
            if (remember) {
                localStorage.setItem('auth_token', data.token);
            } else {
                sessionStorage.setItem('auth_token', data.token);
            }

            // Show success message
            loginSuccess.textContent = '¡Inicio de sesión exitoso! Redirigiendo...';
            loginSuccess.style.display = 'block';

            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 1000);
        } else {
            // Show error message
            loginError.textContent = data.message || 'Error al iniciar sesión';
            loginError.style.display = 'block';
        }
    } catch (error) {
        loginError.textContent = 'Error de conexión. Por favor, intenta de nuevo.';
        loginError.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});

// Register Form Submission
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const passwordConfirm = document.getElementById('register-password-confirm').value;
    const acceptTerms = document.getElementById('accept-terms').checked;

    // Hide previous messages
    registerError.style.display = 'none';
    registerSuccess.style.display = 'none';

    // Validation
    if (password !== passwordConfirm) {
        registerError.textContent = 'Las contraseñas no coinciden';
        registerError.style.display = 'block';
        return;
    }

    if (!acceptTerms) {
        registerError.textContent = 'Debes aceptar los términos y condiciones';
        registerError.style.display = 'block';
        return;
    }

    // Disable submit button
    const submitBtn = registerForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creando cuenta...';

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (response.ok) {
            // Show success message
            registerSuccess.textContent = '¡Cuenta creada exitosamente! Redirigiendo al login...';
            registerSuccess.style.display = 'block';

            // Reset form
            registerForm.reset();

            // Switch to login tab after 2 seconds
            setTimeout(() => {
                document.querySelector('[data-tab="login"]').click();
                // Pre-fill username
                document.getElementById('login-username').value = username;
            }, 2000);
        } else {
            // Show error message
            registerError.textContent = data.message || 'Error al crear la cuenta';
            registerError.style.display = 'block';
        }
    } catch (error) {
        registerError.textContent = 'Error de conexión. Por favor, intenta de nuevo.';
        registerError.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});

// Password Recovery Modal
if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener('click', (e) => {
        e.preventDefault();
        passwordModal.classList.add('active');
    });
}

if (passwordModalClose) {
    passwordModalClose.addEventListener('click', () => {
        passwordModal.classList.remove('active');
    });
}

// Close modal on outside click
if (passwordModal) {
    passwordModal.addEventListener('click', (e) => {
        if (e.target === passwordModal) {
            passwordModal.classList.remove('active');
        }
    });
}

// Password Recovery Form Submission
if (passwordRecoveryForm) {
    passwordRecoveryForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('recovery-email').value;

        // Hide previous messages
        recoveryError.style.display = 'none';
        recoverySuccess.style.display = 'none';

        // Disable submit button
        const submitBtn = passwordRecoveryForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Enviando...';

        try {
            const response = await fetch(`${API_BASE}/auth/password-recovery`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            });

            const data = await response.json();

            if (response.ok) {
                // Show success message
                recoverySuccess.textContent = 'Instrucciones enviadas a tu email';
                recoverySuccess.style.display = 'block';

                // Reset form and close modal after 3 seconds
                setTimeout(() => {
                    passwordRecoveryForm.reset();
                    passwordModal.classList.remove('active');
                    recoverySuccess.style.display = 'none';
                }, 3000);
            } else {
                // Show error message
                recoveryError.textContent = data.message || 'Error al enviar el email';
                recoveryError.style.display = 'block';
            }
        } catch (error) {
            recoveryError.textContent = 'Error de conexión. Por favor, intenta de nuevo.';
            recoveryError.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}

// Check if already logged in
function checkAuth() {
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    if (token) {
        // Verify token is valid
        fetch(`${API_BASE}/auth/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (response.ok) {
                // Redirect to dashboard if already logged in
                window.location.href = '/dashboard.html';
            }
        })
        .catch(error => {
            // Token invalid, continue with login page
            console.log('Token verification failed');
        });
    }
}

// Run auth check on page load
checkAuth();
