#!/bin/bash
# NetGuard - Restaurar configuración de red por defecto
# Uso: sudo ./reset_gateway.sh
# Variables opcionales: LAN_INTERFACE

set -e

LAN="${LAN_INTERFACE:-eth1}"

[ "$EUID" -ne 0 ] && echo "Ejecutar con sudo" && exit 1

echo "=== NetGuard - Restaurando red ==="

# 1) Detener servicios portal
systemctl stop dnsmasq 2>/dev/null || true

# 2) Eliminar configuración dnsmasq del portal
if [ -f /etc/dnsmasq.d/netguard.conf ]; then
  rm -f /etc/dnsmasq.d/netguard.conf
fi

# 3) Reactivar systemd-resolved y restaurar resolv.conf
if systemctl list-unit-files | grep -q systemd-resolved.service; then
  systemctl enable systemd-resolved 2>/dev/null || true
  systemctl start systemd-resolved 2>/dev/null || true
fi

# Si systemd-resolved no se usa, dejar un resolv.conf básico
if [ ! -e /etc/resolv.conf ] || ! grep -qi "nameserver" /etc/resolv.conf; then
  echo "nameserver 8.8.8.8" > /etc/resolv.conf
  echo "nameserver 1.1.1.1" >> /etc/resolv.conf
fi

# 4) Desactivar IP forwarding
sysctl -w net.ipv4.ip_forward=0 >/dev/null 2>&1 || true

# 5) Limpiar iptables (filter y nat)
iptables -F || true
iptables -X || true
iptables -t nat -F || true
iptables -t nat -X || true
iptables -P FORWARD ACCEPT || true

# 6) Retirar IP del portal en LAN (opcional pero recomendado)
ip addr flush dev "$LAN" 2>/dev/null || true

# 7) Reiniciar dnsmasq para reusar config global si existe
systemctl restart dnsmasq 2>/dev/null || true

echo "Red restaurada. Puedes volver a usar la configuración original del sistema."