# Red
PORTAL_IP = "192.168.1.1"
PORTAL_PORT = 80
LAN_INTERFACE = "eth1"
WAN_INTERFACE = "eth0"
LAN_NETWORK = "192.168.1.0/24"

# Servidor HTTP
BUFFER_SIZE = 4096
SOCKET_TIMEOUT = 30

# Archivos
USERS_FILE = "data/users.json"

# Sesiones
SESSION_TIMEOUT = 3600  # 1 hora

# URLs de detección de portal cautivo 
CAPTIVE_DETECTION_PATHS = [
    "/generate_204",
    "/gen_204",
    "/hotspot-detect.html",
    "/ncsi.txt",
    "/connecttest.txt",
    "/success.txt",
]
