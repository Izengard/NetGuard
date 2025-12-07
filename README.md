# NetGuard - Portal Cautivo

Sistema de portal cautivo (captive portal) para autenticación de usuarios en redes locales, implementado completamente en Python sin dependencias externas.

## 📋 Descripción General

NetGuard es un portal cautivo diseñado para controlar el acceso a Internet en redes LAN. Intercepta las peticiones HTTP de dispositivos no autenticados y los redirige a una página de login. Una vez autenticados, permite el tráfico hacia Internet mediante reglas de firewall dinámicas.

## 🏗️ Arquitectura del Sistema

### Componentes Principales

```
NetGuard/
├── src/
│   ├── main.py              # Punto de entrada y orquestador
│   ├── config.py            # Configuración centralizada
│   ├── auth/                # Sistema de autenticación
│   │   ├── users.py         # Gestión de usuarios
│   │   └── sessions.py      # Gestión de sesiones
│   ├── dns/                 # Servidor DNS
│   │   └── dns_server.py    # Redirección DNS al portal
│   ├── firewall/            # Gestión de firewall
│   │   └── manager.py       # Reglas iptables
│   └── http_server/         # Servidor web
│       ├── server.py        # Socket TCP server
│       ├── handlers.py      # Lógica de rutas HTTP
│       └── templates/       # Frontend HTML/CSS/JS
```

### Flujo de Funcionamiento

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Cliente   │─────▶│  DNS Server  │─────▶│   Portal    │
│ No Autent.  │      │ (Port 53)    │      │ (Port 80)   │
└─────────────┘      └──────────────┘      └─────────────┘
       │                                           │
       │              Redirección                  │
       └──────────────────────────────────────────┘
                         Login
                           │
                           ▼
                  ┌─────────────────┐
                  │  Autenticación  │
                  │  + Sesión       │
                  └─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Firewall Rules  │
                  │ (iptables)      │
                  └─────────────────┘
                           │
                           ▼
                     ┌──────────┐
                     │ Internet │
                     └──────────┘
```

## 🔧 Módulos Técnicos

### 1. **Sistema de Autenticación** (`auth/`)

#### `users.py` - UserManager
- **Propósito**: Gestión de credenciales de usuario
- **Características**:
  - Almacenamiento en JSON (`data/users.json`)
  - Hash SHA-256 con salt aleatorio
  - Usuario admin predeterminado (admin/admin123)
  - Métodos: `authenticate()`, `add_user()`, `delete_user()`

**Seguridad**:
```python
# Hash format: "salt:hash"
salt = os.urandom(16).hex()
hash_value = hashlib.sha256((salt + password).encode()).hexdigest()
```

#### `sessions.py` - SessionManager
- **Propósito**: Control de sesiones activas
- **Características**:
  - Mapeo IP ↔ Usuario + MAC + Timestamp
  - Thread de monitoreo (cada 30s)
  - Expiración automática (1 hora por defecto)
  - Detección de MAC spoofing

**Anti-Spoofing**:
```python
# Verifica cambios de MAC para la misma IP
if current_mac != stored_mac:
    revoke_session(ip)
```

### 2. **Servidor DNS** (`dns/`)

#### `dns_server.py` - CaptivePortalDNS
- **Propósito**: Redireccionar todas las consultas DNS al portal
- **Funcionamiento**:
  - Socket UDP en puerto 53
  - Responde a TODAS las consultas con la IP del portal
  - Construcción manual de paquetes DNS (sin librerías)

**Estructura de respuesta DNS**:
```
[Header: 12 bytes] + [Query original] + [Answer: IP del portal]
```

### 3. **Firewall** (`firewall/`)

#### `manager.py` - FirewallManager
- **Propósito**: Control de acceso a nivel de red
- **Tecnología**: iptables (Linux)

**Reglas principales**:
```bash
# 1. Bloquear todo forwarding por defecto
iptables -P FORWARD DROP

# 2. Redireccionar HTTP al portal
iptables -t nat -A PREROUTING -i eth1 -p tcp --dport 80 \
  -j DNAT --to-destination 192.168.1.1:80

# 3. Autorización individual (IP + MAC)
iptables -I FORWARD -s <IP> -m mac --mac-source <MAC> -j ACCEPT

# 4. NAT para salida a Internet
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```

**Anti-Spoofing a nivel firewall**:
- Vinculación IP+MAC obligatoria
- Evita cambio de MAC sin reautenticación

### 4. **Servidor HTTP** (`http_server/`)

#### `server.py` - CaptivePortalServer
- **Propósito**: Servidor web sin dependencias
- **Implementación**:
  - Socket TCP raw (`socket.socket`)
  - Multi-threading (un thread por cliente)
  - Sin frameworks (Flask, Django, etc.)

**Flujo de request**:
```python
1. Accept connection → client_socket
2. Recv raw HTTP request (4096 bytes)
3. Parse request → RequestHandler
4. Generate HTTP response
5. Send response + close socket
```

#### `handlers.py` - RequestHandler
- **Rutas**:
  - `/login` (GET/POST): Autenticación
  - `/status`: Panel de usuario autenticado
  - `/logout`: Cierre de sesión
  - `/generate_204`, `/ncsi.txt`: Detección de portal cautivo

**Detección automática de portales**:
```python
# iOS, Android, Windows usan estas rutas
CAPTIVE_DETECTION_PATHS = [
    "/generate_204",      # Android/Chrome
    "/hotspot-detect.html",  # iOS/macOS
    "/ncsi.txt",          # Windows
]
```

### 5. **Frontend** (`http_server/templates/`)

#### Archivos:
- `login.html`: Formulario de autenticación
- `status.html`: Dashboard post-login
- `style.css`: Estilos responsivos
- `index.js`: Validación y UX (opcional)

**Features**:
- Diseño responsive (mobile-first)
- Sin dependencias externas (no jQuery, Bootstrap, etc.)
- Validación client-side

## ⚙️ Configuración

### `config.py` - Parámetros principales

```python
# Red
PORTAL_IP = "192.168.1.1"      # IP del servidor portal
PORTAL_PORT = 80                # Puerto HTTP
LAN_INTERFACE = "eth1"          # Interfaz hacia clientes
WAN_INTERFACE = "eth0"          # Interfaz hacia Internet
LAN_NETWORK = "192.168.1.0/24"  # Subred LAN

# Sesiones
SESSION_TIMEOUT = 3600          # 1 hora en segundos

# Archivos
USERS_FILE = "data/users.json"
TEMPLATES_DIR = "http_server/templates"
```

## 🚀 Instalación y Uso

### Requisitos
- **Sistema Operativo**: Linux (Ubuntu/Debian/CentOS)
- **Python**: 3.6+
- **Privilegios**: root/sudo (para iptables)
- **Red**: 2 interfaces de red (LAN + WAN)

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/Izengard/NetGuard.git
cd NetGuard/src

# No requiere pip install (sin dependencias)
```

### Ejecución

```bash
# Modo completo (requiere root)
sudo python3 main.py

# Modo sin firewall (pruebas)
python3 main.py --no-firewall

# Modo sin DNS
sudo python3 main.py --no-dns

# Agregar usuario
python3 main.py --add-user
```

### Comandos principales

```bash
# Agregar usuario manualmente
python3 main.py --add-user
# Usuario: juan
# Contraseña: ****

# Verificar reglas de firewall
sudo iptables -L -n -v
sudo iptables -t nat -L -n -v

# Ver sesiones activas (en logs)
sudo python3 main.py | grep SESSION
```

## 🔒 Seguridad

### Características de Seguridad

1. **Hashing de contraseñas**:
   - SHA-256 con salt único por usuario
   - No se almacenan contraseñas en texto plano

2. **Anti-Spoofing**:
   - Vinculación IP+MAC en firewall
   - Monitoreo continuo de cambios de MAC
   - Revocación automática si se detecta suplantación

3. **Gestión de sesiones**:
   - Timeout automático (1 hora)
   - Limpieza periódica de sesiones expiradas
   - Thread-safe (locks para concurrencia)

4. **Firewall**:
   - Política restrictiva por defecto (DROP)
   - Autorización individual por usuario
   - Cleanup automático al cerrar



## 🛠️ Desarrollo

### Estructura de Datos

**Sesión activa**:
```python
{
    'username': 'admin',
    'login_time': 1733567890.123,
    'mac': '00:11:22:33:44:55'
}
```

**Usuario en JSON**:
```json
{
    "admin": "a1b2c3d4:sha256hash..."
}
```

## 📝 Licencia

Este proyecto es de código abierto para fines educativos.

## 👤 Autor

**Izengard**  
GitHub: [@Izengard](https://github.com/Izengard)


