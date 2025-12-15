# NetGuard - Portal Cautivo

Sistema de portal cautivo (captive portal) para autenticación de usuarios en redes locales, implementado completamente en Python sin dependencias externas.

## 📋 Descripción General

NetGuard es un portal cautivo diseñado para controlar el acceso a Internet en redes LAN. Intercepta las peticiones HTTP de dispositivos no autenticados y los redirige a una página de login. Una vez autenticados, permite el tráfico hacia Internet mediante reglas de firewall dinámicas.

## 🏗️ Arquitectura del Sistema

### Componentes Principales

```
```text
NetGuard/
├── README.md                # Documentación del proyecto
├── scripts/
│   ├── setup_gateway.sh     # Configuración del sistema
│   └── reset_gateway.sh     # Restaurar red y reglas
├── src/
│   ├── main.py              # Punto de entrada y orquestador
│   ├── config.py            # Configuración centralizada
│   ├── system_setup.py      # Configuración del sistema (Python)
│   ├── auth/                # Sistema de autenticación
│   │   ├── users.py         # Gestión de usuarios
│   │   └── sessions.py      # Gestión de sesiones
│   ├── data/
│   │   └── users.json       # Base de datos de usuarios
│   ├── dns/                 # Servidor DNS
│   │   └── dns_server.py    # Redirección DNS al portal
│   ├── firewall/            # Gestión de firewall
│   │   └── manager.py       # Reglas iptables
│   └── http_server/         # Servidor web
│       ├── server.py        # Socket TCP server
│       ├── handlers.py      # Lógica de rutas HTTP
│       └── templates/       # Frontend HTML/CSS
│           ├── login.html
│           └── status.html
```

## 🐳 Pruebas con Docker

Requisitos: Docker y Docker Compose.

### Levantar entorno de prueba

```bash
# Construir imágenes
docker compose build

# Levantar portal (sin firewall para pruebas rápidas)
docker compose up -d

# Ver contenedores
docker compose ps
```

### Probar desde el contenedor cliente

```bash
# Abrir shell en el cliente
docker exec -it netguard_client sh

# Dentro del cliente
wget -qO- http://192.168.1.1/login    # Probar HTTP del portal
# Si activas el servidor DNS del portal:
dig @192.168.1.1 example.com
```

### Activar firewall dentro del contenedor (opcional)

- Edita `docker-compose.yml` y quita `--no-firewall` del command de `netguard`.
- Añade `privileged: true` al servicio `netguard` para permitir iptables dentro del contenedor.
- Vuelve a levantar: `docker compose up -d --force-recreate`.

> Nota: las reglas iptables vivirán dentro del contenedor, no en el host.

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

```text
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

#### Archivos

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

# WiFi Hotspot
WIFI_INTERFACE = "wlan0"        # Interfaz WiFi
WIFI_SSID = "NetGuard"          # Nombre de la red
WIFI_PASSWORD = "netguard123"   # Contraseña WPA2
WIFI_CHANNEL = 6                # Canal WiFi

# Sesiones
SESSION_TIMEOUT = 3600          # 1 hora en segundos

# Archivos
USERS_FILE = "data/users.json"
TEMPLATES_DIR = "http_server/templates"
```

## 📶 Modo WiFi Hotspot

NetGuard puede funcionar como un punto de acceso WiFi (hotspot), ideal para:
- Crear redes de invitados con autenticación
- Eventos y conferencias
- Espacios públicos (cafeterías, bibliotecas)
- Raspberry Pi como router portátil

### Requisitos WiFi

- Interfaz WiFi con soporte **AP mode** (modo Access Point)
- Paquetes: `hostapd`, `dnsmasq`, `iw`
- Privilegios root

### Verificar soporte AP mode

```bash
# Listar interfaces WiFi
iw dev

# Verificar modos soportados (buscar "AP")
iw list | grep -A 10 "Supported interface modes"
```

### Configuración Automática

```bash
# 1. Ejecutar script de configuración
chmod +x scripts/setup_wifi_hotspot.sh
sudo WIFI_INTERFACE=wlan0 WIFI_SSID="MiRed" WIFI_PASSWORD="password123" ./scripts/setup_wifi_hotspot.sh

# 2. Iniciar portal con WiFi
cd src
sudo python3 main.py --wifi
```

### Opciones de línea de comandos WiFi

```bash
# Usar WiFi como interfaz LAN
sudo python3 main.py --wifi

# Solo iniciar hotspot (sin portal HTTP)
sudo python3 main.py --wifi-only

# Personalizar configuración
sudo python3 main.py --wifi --wifi-interface wlan1 --wifi-ssid "Invitados" --wifi-password "guest2024"
```

### Arquitectura WiFi Hotspot

```text
                    ┌─────────────────────────────────────────┐
                    │           SERVIDOR NetGuard              │
                    │  ┌─────────┐   ┌──────────┐   ┌───────┐ │
[Internet] ──────── │  │  eth0   │ ↔ │ Firewall │ ↔ │ wlan0 │ │
                    │  │  (WAN)  │   │ iptables │   │  (AP) │ │
                    │  └─────────┘   └──────────┘   └───────┘ │
                    │                                    │     │
                    │  ┌──────────┐   ┌────────┐   ┌────────┐ │
                    │  │ Portal   │ ↔ │  DNS   │ ↔ │ DHCP   │ │
                    │  │ HTTP:80  │   │ :53    │   │dnsmasq │ │
                    │  └──────────┘   └────────┘   └────────┘ │
                    └─────────────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
               📱 Móvil            💻 Laptop           📟 Tablet
               (WiFi)               (WiFi)              (WiFi)
```

### Detener WiFi Hotspot

```bash
# Detener portal y restaurar WiFi
sudo ./scripts/reset_wifi_hotspot.sh

# O restaurar manualmente
sudo systemctl stop hostapd
sudo systemctl start NetworkManager
```

### Configuración en Raspberry Pi

```bash
# Instalar dependencias
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq iptables

# Configurar hotspot
sudo WIFI_INTERFACE=wlan0 WIFI_SSID="NetGuard-Pi" ./scripts/setup_wifi_hotspot.sh

# Iniciar portal
cd src && sudo python3 main.py --wifi
```

## 🌐 Configuración del Sistema como Gateway

El servidor debe tener **2 interfaces de red** y configurarse como router.

### Topología de Red

```text
[Internet] → [Router ISP] → [WAN: eth0] → [SERVIDOR] → [LAN: eth1] → [Clientes]
                              192.168.0.x              192.168.1.1    192.168.1.x
```

### Requisitos

- **OS**: Ubuntu 20.04+ / Debian 10+
- **Python**: 3.6+
- **Paquetes**: `iptables`, `dnsmasq`
- **Red**: 2 interfaces (LAN + WAN)

---

## ⚡ Configuración Automática (Recomendado)

```bash
# 1. Identificar interfaces
ip link show                    # Ver interfaces disponibles
ip route | grep default         # WAN = interfaz con ruta por defecto

# 2. Ejecutar script de configuración
chmod +x scripts/setup_gateway.sh
sudo LAN_INTERFACE=eth1 WAN_INTERFACE=eth0 ./scripts/setup_gateway.sh

# 3. Editar config.py con tus interfaces
nano src/config.py
```

---

## 🔧 Configuración Manual

Si prefieres configurar manualmente:

### 1. Configurar IP en interfaz LAN

```bash
sudo ip addr add 192.168.1.1/24 dev eth1
sudo ip link set eth1 up
```

### 3. Configurar DHCP (dnsmasq)

```bash
sudo apt install dnsmasq -y
sudo tee /etc/dnsmasq.d/netguard.conf << EOF
interface=eth1
bind-interfaces
port=0
dhcp-range=192.168.1.100,192.168.1.200,12h
dhcp-option=option:router,192.168.1.1
dhcp-option=option:dns-server,192.168.1.1
EOF
sudo systemctl restart dnsmasq
```

### 4. Deshabilitar systemd-resolved (si está activo)

```bash
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

---

## 🖥️ En Máquina Virtual

**VirtualBox:**

- Adaptador 1 (WAN): NAT
- Adaptador 2 (LAN): Red interna

**VMware:**

- Adapter 1 (WAN): NAT
- Adapter 2 (LAN): Host-only

---

## 🚀 Instalación y Uso

```bash
# 1. Clonar repositorio
git clone https://github.com/Izengard/NetGuard.git
cd NetGuard

# 2. Configurar sistema (ver sección anterior)
sudo LAN_INTERFACE=eth1 WAN_INTERFACE=eth0 ./scripts/setup_gateway.sh

# 3. Ajustar config.py con tus interfaces
nano src/config.py

# 4. Iniciar portal
cd src
sudo python3 main.py
```

### Detener y restaurar red

```bash
# Detener portal y restaurar configuración de red
sudo ./scripts/reset_gateway.sh
```

### Opciones de Ejecución

```bash
sudo python3 main.py              # Modo completo (LAN ethernet)
python3 main.py --no-firewall     # Sin firewall (pruebas)
sudo python3 main.py --no-dns     # Sin servidor DNS
python3 main.py --add-user        # Agregar usuario

# Modo WiFi Hotspot
sudo python3 main.py --wifi       # Portal + WiFi hotspot
sudo python3 main.py --wifi-only  # Solo hotspot WiFi
sudo python3 main.py --wifi --wifi-ssid "MiRed" --wifi-password "clave123"
```

### Comandos Útiles

```bash
# Ver estado del sistema
sudo python3 system_setup.py

# Ver reglas de firewall
sudo iptables -L -n -v
sudo iptables -t nat -L -n -v

# Ver clientes DHCP
cat /var/lib/misc/dnsmasq.leases

# Probar portal
curl -v http://192.168.1.1/login
```

## 🔒 Seguridad

- **Hashing**: SHA-256 con salt único por usuario
- **Anti-Spoofing**: Vinculación IP+MAC, detección de cambios
- **Sesiones**: Timeout automático, limpieza periódica
- **Firewall**: Política DROP por defecto, autorización individual

## 🛠️ Estructuras de Datos

**Sesión activa**:

```python
{'username': 'admin', 'login_time': 1733567890.123, 'mac': '00:11:22:33:44:55'}
```

**Usuario en JSON**:

```json
{"admin": "salt:sha256hash..."}
```

## 📝 Licencia

Código abierto para fines educativos.

## 👤 Autor

**Izengard** - [@Izengard](https://github.com/Izengard)


