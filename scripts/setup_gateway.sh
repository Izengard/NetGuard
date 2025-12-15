# Uso: sudo ./setup_gateway.sh

set -e

# Configuración (editar o pasar como variables de entorno)
LAN="${LAN_INTERFACE:-eth1}"
WAN="${WAN_INTERFACE:-eth0}"
IP="${PORTAL_IP:-192.168.1.1}"
DHCP_START="${DHCP_RANGE_START:-192.168.1.100}"
DHCP_END="${DHCP_RANGE_END:-192.168.1.200}"

# Verificar root
[ "$EUID" -ne 0 ] && echo "Ejecutar con sudo" && exit 1

echo "=== NetGuard - Configuración del Gateway ==="
echo "LAN: $LAN | WAN: $WAN | IP: $IP"
echo ""

HAS_SYSTEMCTL=false
if command -v systemctl >/dev/null 2>&1; then
    HAS_SYSTEMCTL=true
fi

# 1. Instalar dependencias
echo "[1/4] Instalando dependencias..."
apt-get update -qq
apt-get install -y -qq iptables dnsmasq

# 2. Configurar IP en interfaz LAN
echo "[2/4] Configurando interfaz LAN..."
ip addr flush dev "$LAN" 2>/dev/null || true
ip addr add "$IP/24" dev "$LAN"
ip link set "$LAN" up

echo "[3/4] Deshabilitando systemd-resolved..."
if $HAS_SYSTEMCTL && systemctl is-active --quiet systemd-resolved; then
    systemctl stop systemd-resolved
    systemctl disable systemd-resolved
    rm -f /etc/resolv.conf
    echo "nameserver 8.8.8.8" > /etc/resolv.conf
fi

# 4. Configurar DHCP (dnsmasq)
echo "[4/4] Configurando servidor DHCP..."

cat > /etc/dnsmasq.d/netguard.conf << EOF
interface=$LAN
bind-interfaces
port=0
dhcp-range=$DHCP_START,$DHCP_END,12h
dhcp-option=option:router,$IP
dhcp-option=option:dns-server,$IP
EOF

if $HAS_SYSTEMCTL; then
    systemctl stop dnsmasq 2>/dev/null || true
    systemctl restart dnsmasq
    systemctl enable dnsmasq 2>/dev/null || true
else
    # Entorno sin systemd (por ejemplo, contenedores)
    if [ -f /var/run/dnsmasq.pid ]; then
        kill "$(cat /var/run/dnsmasq.pid)" 2>/dev/null || true
        rm -f /var/run/dnsmasq.pid
    fi
    dnsmasq --conf-file=/etc/dnsmasq.d/netguard.conf --keep-in-foreground --log-facility=- &
fi

echo ""
echo "=== Configuración completada ==="
echo "Interfaz $LAN configurada con IP $IP"
echo "DHCP activo: $DHCP_START - $DHCP_END"
echo ""
echo "Iniciar portal: cd src && sudo python3 main.py"
