#!/bin/bash
# NetGuard - Restaurar WiFi a estado normal
# Uso: sudo ./reset_wifi_hotspot.sh

set -e

WIFI="${WIFI_INTERFACE:-wlan0}"

[ "$EUID" -ne 0 ] && echo "Ejecutar con sudo" && exit 1

echo "=== NetGuard - Restaurando WiFi ==="

# 1. Detener servicios del hotspot
echo "[1/5] Deteniendo servicios..."
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
pkill -9 hostapd 2>/dev/null || true

# 2. Eliminar configuraciones del portal
echo "[2/5] Limpiando configuraciones..."
rm -f /etc/hostapd/hostapd.conf
rm -f /etc/dnsmasq.d/netguard-wifi.conf
rm -f /tmp/netguard_hostapd.conf
rm -f /tmp/netguard_dnsmasq_wifi.conf

# 3. Limpiar interfaz WiFi
echo "[3/5] Restaurando interfaz WiFi..."
ip addr flush dev "$WIFI" 2>/dev/null || true
ip link set "$WIFI" down 2>/dev/null || true

# 4. Restaurar servicios de red normales
echo "[4/5] Restaurando servicios de red..."
systemctl start NetworkManager 2>/dev/null || true
systemctl start wpa_supplicant 2>/dev/null || true

# 5. Limpiar iptables
echo "[5/5] Limpiando reglas de firewall..."
iptables -F 2>/dev/null || true
iptables -t nat -F 2>/dev/null || true
iptables -P FORWARD ACCEPT 2>/dev/null || true

# Deshabilitar IP forwarding
sysctl -w net.ipv4.ip_forward=0 > /dev/null 2>&1 || true

echo ""
echo "=== WiFi restaurado ==="
echo "Puedes reconectarte a tu red WiFi normal."
echo ""
echo "Si usas NetworkManager, ejecuta:"
echo "  nmcli device wifi list"
echo "  nmcli device wifi connect <SSID> password <PASSWORD>"
