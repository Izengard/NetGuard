# Red

PORTAL_IP = "192.168.100.1"

PORTAL_PORT = 8080

LAN_INTERFACE = "wlp4s0"

WAN_INTERFACE = "enxfab7943b1200"

LAN_NETWORK = "192.168.100.0/24"

DHCP_START = "192.168.100.100"

DHCP_END = "192.168.100.200"

EXTERNAL_DNS = "8.8.8.8"
# WiFi Hotspot Configuration

WIFI_SSID = "NetGuard"             # Nombre de la red WiFi

WIFI_PASSWORD = "netguard123"      # Contraseña WPA2 (mínimo 8 caracteres, vacío = red abierta)

WIFI_CHANNEL = 6                   # Canal WiFi (1-11)

WIFI_MODE = "hotspot"              # Modo: "hotspot" (AP) o "client"


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

    "/library/test/success.html",  # Apple iOS/macOS

    "/kindle-wifi/wifistub.html",  # Amazon Kindle

]

