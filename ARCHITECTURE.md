# Arquitectura de Conquer Web - Nueva Interfaz

<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

## Visión General

Esta versión mejorada de Conquer Web reemplaza la autenticación HTTP Basic Auth con una interfaz web moderna que incluye páginas de login personalizadas, dashboard de jugadores, sistema de cuentas individuales y panel de administración.

## Arquitectura del Sistema

```
┌────────────────────────────────────────────────────────────┐
│                    NAVEGADOR (HTTPS)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  Landing     │  │   Login      │  │   Dashboard      │ │
│  │  (index.html)│  │ (login.html) │  │ (dashboard.html) │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
│  ┌──────────────┐  ┌──────────────────────────────────────┐│
│  │    Help      │  │         Admin Panel                  ││
│  │ (help.html)  │  │       (admin.html)                   ││
│  └──────────────┘  └──────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
                              ↓ HTTPS
┌────────────────────────────────────────────────────────────┐
│              APACHE (Reverse Proxy + SSL)                   │
│  - Puerto 443 (HTTPS)                                       │
│  - Proxy /api → backend:3000                                │
│  - Proxy /play → conquer:7681 (ttyd)                        │
│  - Proxy / → backend:3000 (frontend estático)               │
└─────────────┬────────────────┬──────────────────────────────┘
              │                │
              ↓                ↓
   ┌──────────────────┐  ┌─────────────────┐
   │   BACKEND API    │  │  TTYD + CONQUER │
   │  (Node.js:3000)  │  │   (Docker:7681) │
   │                  │  │                 │
   │ - Express.js     │  │ - Terminal Web  │
   │ - JWT Auth       │  │ - Juego Conquer │
   │ - SQLite DB      │  │                 │
   │ - REST API       │  └─────────────────┘
   │ - Archivos       │
   │   estáticos      │
   └────────┬─────────┘
            ↓
   ┌─────────────────┐
   │  BASE DE DATOS  │
   │    (SQLite)     │
   │                 │
   │ - Usuarios      │
   │ - Sesiones      │
   │ - Estadísticas  │
   └─────────────────┘
```

## Componentes

### 1. Frontend (HTML/CSS/JavaScript)

**Ubicación:** `/frontend/`

**Páginas:**
- `index.html` - Landing page con información del juego
- `login.html` - Login y registro de usuarios
- `dashboard.html` - Panel del jugador con estadísticas y acceso al juego
- `help.html` - Guía completa del juego
- `admin.html` - Panel de administración (solo admins)

**Estilos:**
- `/frontend/css/styles.css` - CSS completo con tema oscuro y diseño responsive

**Scripts:**
- `/frontend/js/auth.js` - Gestión de login/registro
- `/frontend/js/dashboard.js` - Lógica del dashboard
- `/frontend/js/admin.js` - Panel de administración
- `/frontend/js/status.js` - Estado del servidor en tiempo real
- `/frontend/js/help.js` - Navegación de ayuda

**Características:**
- Diseño moderno con tema oscuro
- Totalmente responsive (mobile-first)
- Autenticación basada en JWT
- Actualizaciones en tiempo real
- Sin dependencias externas (vanilla JavaScript)

### 2. Backend API (Node.js + Express)

**Ubicación:** `/backend/`

**Estructura:**
```
backend/
├── src/
│   ├── server.js           # Servidor principal
│   ├── database.js         # Configuración de SQLite
│   ├── middleware/
│   │   └── auth.js         # Middleware de autenticación
│   └── routes/
│       ├── auth.js         # Rutas de autenticación
│       ├── user.js         # Rutas de usuario
│       ├── admin.js        # Rutas de administración
│       └── status.js       # Estado del servidor
├── db/
│   └── conquer.db          # Base de datos SQLite
├── package.json
├── Dockerfile
└── .env.example
```

**API Endpoints:**

#### Autenticación
- `POST /api/auth/register` - Registro de usuarios
- `POST /api/auth/login` - Inicio de sesión
- `GET /api/auth/verify` - Verificar token JWT
- `POST /api/auth/refresh` - Refrescar token
- `POST /api/auth/logout` - Cerrar sesión
- `POST /api/auth/password-recovery` - Recuperar contraseña

#### Usuario
- `GET /api/user/stats` - Estadísticas del usuario

#### Estado del Servidor
- `GET /api/status` - Estado general del servidor
- `GET /api/players/online` - Jugadores conectados
- `GET /api/world/stats` - Estadísticas del mundo
- `GET /api/ranking` - Ranking de jugadores
- `GET /api/news` - Noticias del juego

#### Administración (requiere rol admin)
- `GET /api/admin/services` - Estado de servicios
- `GET /api/admin/resources` - Recursos del sistema (CPU, RAM, disco)
- `GET /api/admin/users` - Lista de usuarios
- `GET /api/admin/sessions` - Sesiones activas
- `GET /api/admin/world` - Información del mundo
- `POST /api/admin/world/backup` - Crear backup
- `GET /api/admin/logs` - Ver logs del sistema
- `GET /api/admin/statistics` - Estadísticas generales
- `POST /api/admin/config` - Actualizar configuración

### 3. Base de Datos (SQLite)

**Ubicación:** `/backend/db/conquer.db`

**Esquema:**

#### Tabla: users
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'player',
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    score INTEGER DEFAULT 0,
    battles INTEGER DEFAULT 0,
    cities INTEGER DEFAULT 0,
    playtime INTEGER DEFAULT 0
)
```

#### Tabla: sessions
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    ip TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
```

#### Tabla: game_stats
```sql
CREATE TABLE game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_id TEXT,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    result TEXT,
    score INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
```

#### Tabla: news
```sql
CREATE TABLE news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

#### Tabla: logs
```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    user_id INTEGER,
    ip TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### 4. Contenedor Conquer + ttyd

**Ubicación:** `/conquer/`

**Cambios respecto a versión anterior:**
- Mejorada configuración de ttyd con tema personalizado
- Fuente más legible (tamaño 18px, Cascadia Code)
- Tema oscuro para mejor legibilidad
- Cursor parpadeante
- Ya no se usa HTTP Basic Auth (autenticación ahora en el backend)

### 5. Apache (Reverse Proxy)

**Configuración:** `/apache/local.conf`

**Rutas de Proxy:**
```
/api/*      → backend:3000     (API REST)
/play/*     → conquer:7681     (Terminal de juego con WebSocket)
/*          → backend:3000     (Frontend estático)
```

**Características:**
- SSL/TLS terminación
- WebSocket support para ttyd
- Compresión GZIP
- Security headers (HSTS, CSP, etc.)
- Logs de acceso

## Flujo de Autenticación

### 1. Registro de Usuario
```
Usuario → Login Page → Backend API (/api/auth/register)
                              ↓
                         Hash password (bcrypt)
                              ↓
                       Insertar en DB
                              ↓
                       Respuesta exitosa
```

### 2. Inicio de Sesión
```
Usuario → Login Page → Backend API (/api/auth/login)
                              ↓
                    Verificar usuario y contraseña
                              ↓
                    Generar JWT token
                              ↓
                    Guardar sesión en DB
                              ↓
                    Enviar token al cliente
                              ↓
                    Guardar en localStorage/sessionStorage
                              ↓
                    Redirigir a Dashboard
```

### 3. Acceso a Recursos Protegidos
```
Cliente → Request con "Authorization: Bearer <token>"
              ↓
      Backend verifica JWT
              ↓
      Validar sesión en DB
              ↓
      Si válido: procesar request
      Si inválido: 401 Unauthorized
```

### 4. Acceso al Juego
```
Dashboard → Click "Entrar al Juego"
                  ↓
         Redirect a /play con token
                  ↓
         Apache proxy a ttyd
                  ↓
         Terminal WebSocket abierto
                  ↓
         Juego Conquer ejecutándose
```

## Gestión de Sesiones

**Duración de Sesión:**
- Con "Recordarme": 7 días
- Sin "Recordarme": 24 horas

**Advertencia de Expiración:**
- 5 minutos antes de expirar: modal de advertencia
- Opción de extender sesión (refresh token)

**Límite de Sesiones Concurrentes:**
- Controlado por MAX_CLIENTS (default: 5)
- Solo admins pueden ver sesiones activas

## Seguridad

### Autenticación
- Contraseñas hasheadas con bcrypt (10 rounds)
- JWT con secret key configurable
- Tokens expiran automáticamente
- Sesiones almacenadas en DB para invalidación

### Autorización
- Middleware verifyToken para rutas protegidas
- Middleware requireAdmin para rutas de administración
- Validación de roles en cada request

### Protección de Datos
- Variables de entorno para secrets (.env)
- No se exponen contraseñas ni tokens en logs
- HTTPS obligatorio (redirect de HTTP a HTTPS)

### Headers de Seguridad (Apache)
- HSTS (HTTP Strict Transport Security)
- CSP (Content Security Policy)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection

## Despliegue

### Desarrollo Local

```bash
# 1. Configurar variables de entorno
./setup-environment.sh  # Opción 1: Local

# 2. Generar mundo (si no existe)
./generate-world.sh

# 3. Iniciar servicios
docker-compose -f docker-compose.local.yml up -d

# 4. Acceder
https://localhost
```

### Producción (VPS)

```bash
# 1. Configurar variables de entorno
./setup-environment.sh  # Opción 2: VPS

# 2. Generar mundo (si no existe)
./generate-world.sh

# 3. Desplegar
sudo ./deploy-to-vps.sh

# 4. Acceder
https://tu-dominio.com
```

## Monitoreo y Administración

### Panel de Administración

**Acceso:** https://tu-dominio.com/admin.html

**Funcionalidades:**
- Ver estado de servicios (backend, ttyd, database)
- Monitorear recursos del sistema (CPU, RAM, disco)
- Gestionar usuarios (crear, editar, desactivar)
- Ver sesiones activas y cerrarlas
- Gestión del mundo (backup, restore, reset)
- Ver logs del sistema
- Estadísticas globales
- Configuración del servidor

### Usuario Administrador por Defecto

**Credenciales iniciales:**
- Usuario: `admin`
- Contraseña: `admin123`

**⚠️ IMPORTANTE:** Cambiar esta contraseña inmediatamente después del primer login.

## Escalabilidad

### Mejoras Futuras

1. **Base de Datos:**
   - Migrar a PostgreSQL para mejor rendimiento
   - Implementar cache con Redis

2. **Sesiones:**
   - Almacenar sesiones en Redis para múltiples instancias
   - Load balancing con múltiples backends

3. **Juego:**
   - Múltiples instancias de ttyd
   - Asignación dinámica de jugadores a instancias

4. **Notificaciones:**
   - WebSocket para notificaciones en tiempo real
   - Push notifications para móviles

## Mantenimiento

### Backups

```bash
# Backup de base de datos
cp backend/db/conquer.db backend/db/conquer_backup_$(date +%Y%m%d).db

# Backup del mundo
./backup-world.sh
```

### Logs

```bash
# Logs del backend
docker logs conquer-backend

# Logs de Apache
docker logs apache-local

# Logs del juego
docker logs conquer-local
```

### Actualizaciones

```bash
# Reconstruir contenedores
./rebuild.sh --force

# Reiniciar servicios
docker-compose -f docker-compose.local.yml restart
```

## Diferencias con la Versión Anterior

| Característica | Versión Anterior | Nueva Versión |
|----------------|------------------|---------------|
| Autenticación | HTTP Basic Auth (popup) | Login page personalizada |
| Usuarios | Usuario/contraseña compartidos | Cuentas individuales |
| Frontend | ttyd directo | Interfaz web completa |
| Dashboard | No | Sí |
| Estadísticas | No | Sí |
| Admin Panel | Línea de comandos | Interfaz web |
| Base de Datos | No | SQLite |
| Backend | No | Node.js + Express |
| Gestión de Sesiones | Solo timeout | Advertencias, extensión |
| Responsive | Limitado | Completo |

## Licencia

GPL-3.0-or-later

Copyright 2025 Juan Manuel Méndez Rey
