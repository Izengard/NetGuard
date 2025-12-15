#!/bin/bash
# NetGuard - Configuración de WiFi Hotspot
# Uso: sudo ./setup_wifi_hotspot.sh
#
# Variables de entorno opcionales:
#   WIFI_INTERFACE  - Interfaz WiFi (default: wlan0)
#   WIFI_SSID       - Nombre de la red (default: NetGuard)
#   WIFI_PASSWORD   - Contraseña WPA2 (default: netguard123)
#   WIFI_CHANNEL    - Canal WiFi 1-11 (default: 6)
#   PORTAL_IP       - IP del portal (default: 192.168.1.1)

set -e

# Configuración
WIFI="${WIFI_INTERFACE:-wlan0}"
SSID="${WIFI_SSID:-NetGuard}"
PASSWORD="${WIFI_PASSWORD:-netguard123}"
CHANNEL="${WIFI_CHANNEL:-6}"
IP="${PORTAL_IP:-192.168.1.1}"
DHCP_START="${DHCP_RANGE_START:-192.168.1.100}"
DHCP_END="${DHCP_RANGE_END:-192.168.1.200}"

# Verificar root
[ "$EUID" -ne 0 ] && echo "Ejecutar con sudo" && exit 1

echo "=============================================="
echo "   NetGuard - Configuración WiFi Hotspot"
echo "=============================================="
echo "Interfaz: $WIFI"
echo "SSID: $SSID"
echo "Canal: $CHANNEL"
echo "IP: $IP"
echo ""

# Verificar que la interfaz existe
if ! ip link show "$WIFI" > /dev/null 2>&1; then
    echo "[ERROR] Interfaz $WIFI no encontrada"
    echo ""
    echo "Interfaces WiFi disponibles:"
    iw dev 2>/dev/null | grep Interface | awk '{print "  - " $2}' || \
    ls /sys/class/net/ | xargs -I{} sh -c 'test -d /sys/class/net/{}/wireless && echo "  - {}"'
    exit 1
fi

# 1. Instalar dependencias
echo "[1/6] Instalando dependencias..."
apt-get update -qq
apt-get install -y -qq hostapd dnsmasq iptables iw wireless-tools

# 2. Detener servicios conflictivos
echo "[2/6] Deteniendo servicios conflictivos..."
systemctl stop NetworkManager 2>/dev/null || true
systemctl stop wpa_supplicant 2>/dev/null || true
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true

# Matar procesos que puedan estar usando la interfaz
pkill -9 wpa_supplicant 2>/dev/null || true
pkill -9 hostapd 2>/dev/null || true
rfkill unblock wifi 2>/dev/null || true

sleep 1

# 3. Configurar interfaz WiFi
echo "[3/6] Configurando interfaz WiFi..."
ip link set "$WIFI" down
ip addr flush dev "$WIFI"
ip link set "$WIFI" up
ip addr add "$IP/24" dev "$WIFI"

# 4. Configurar hostapd
echo "[4/6] Configurando Access Point (hostapd)..."
HOSTAPD_CONF="/etc/hostapd/hostapd.conf"
mkdir -p /etc/hostapd

# Determinar si usar contraseña o red abierta
if [ ${#PASSWORD} -ge 8 ]; then
    cat > "$HOSTAPD_CONF" << EOF
# NetGuard WiFi Hotspot Configuration
interface=$WIFI
driver=nl80211
ssid=$SSID
hw_mode=g
channel=$CHANNEL
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF
    echo "   Tipo: Red protegida WPA2"
else
    cat > "$HOSTAPD_CONF" << EOF
# NetGuard WiFi Hotspot Configuration (Open Network)
interface=$WIFI
driver=nl80211
ssid=$SSID
hw_mode=g
channel=$CHANNEL
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
EOF
    echo "   Tipo: Red abierta (sin contraseña)"
fi

# Configurar hostapd para usar este archivo
echo "DAEMON_CONF=\"$HOSTAPD_CONF\"" > /etc/default/hostapd

# 5. Configurar DHCP con dnsmasq
echo "[5/6] Configurando servidor DHCP..."
cat > /etc/dnsmasq.d/netguard-wifi.conf << EOF
# NetGuard WiFi DHCP Configuration
interface=$WIFI
bind-interfaces
port=0
dhcp-range=$DHCP_START,$DHCP_END,12h
dhcp-option=option:router,$IP
dhcp-option=option:dns-server,$IP
dhcp-authoritative
EOF

# 6. Habilitar IP forwarding
echo "[6/6] Habilitando IP forwarding..."
sysctl -w net.ipv4.ip_forward=1 > /dev/null

# Iniciar servicios
echo ""
echo "Iniciando servicios..."

# Iniciar hostapd
systemctl unmask hostapd 2>/dev/null || true
systemctl start hostapd
if ! systemctl is-active --quiet hostapd; then
    echo "[ERROR] hostapd no pudo iniciar"
    echo "Verificar logs: journalctl -u hostapd -n 50"
    exit 1
fi

# Iniciar dnsmasq
systemctl start dnsmasq
if ! systemctl is-active --quiet dnsmasq; then
    echo "[ERROR] dnsmasq no pudo iniciar"
    echo "Verificar logs: journalctl -u dnsmasq -n 50"
    exit 1
fi

echo ""
echo "=============================================="
echo "   ✓ WiFi Hotspot Configurado"
echo "=============================================="
echo "SSID: $SSID"
if [ ${#PASSWORD} -ge 8 ]; then
    echo "Contraseña: $PASSWORD"
else
    echo "Contraseña: (ninguna - red abierta)"
fi
echo "IP del Portal: $IP"
echo "DHCP: $DHCP_START - $DHCP_END"
echo ""
echo "Para iniciar el portal cautivo:"
echo "  cd src && sudo python3 main.py --wifi"
echo ""
echo "Para detener el hotspot:"
echo "  sudo ./reset_wifi_hotspot.sh"
echo "=============================================="
