import subprocess
import threading

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAN_INTERFACE, WAN_INTERFACE, PORTAL_IP, PORTAL_PORT, EXTERNAL_DNS


class FirewallManager:
    
    def __init__(self):
        self.authorized_ips = set()
        self.lock = threading.Lock()
    
    def _run(self, cmd: str) -> bool:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def initialize_rules(self) -> bool:
        
        commands = [
            # Limpiar reglas
            "iptables -F",
            "iptables -X",
            "iptables -t nat -F",
            
            # Políticas por defecto
            "iptables -P INPUT ACCEPT",
            "iptables -P OUTPUT ACCEPT",
            "iptables -P FORWARD DROP",  # Bloquear reenvío por defecto
            
            # Permitir conexiones establecidas
            "iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT",
            
            # Permitir acceso al portal y DNS
            f"iptables -A INPUT -i {LAN_INTERFACE} -p tcp --dport {PORTAL_PORT} -j ACCEPT",
            f"iptables -A INPUT -i {LAN_INTERFACE} -p udp --dport 53 -j ACCEPT",
            
            # Redirigir HTTP al portal cautivo
            f"iptables -t nat -A PREROUTING -i {LAN_INTERFACE} -p tcp --dport 80 "
            f"-j DNAT --to-destination {PORTAL_IP}:{PORTAL_PORT}",
            
            # NAT para salida a Internet
            f"iptables -t nat -A POSTROUTING -o {WAN_INTERFACE} -j MASQUERADE",
        ]
        
        for cmd in commands:
            if not self._run(cmd):
                print(f"[FIREWALL] Error ejecutando: {cmd}")
                return False
        
        # Habilitar IP forwarding 
        self._run("sysctl -w net.ipv4.ip_forward=1")
        
        print("[FIREWALL] Reglas inicializadas")
        return True
    
    def authorize_ip(self, ip: str, mac: str ) -> bool:
    
        with self.lock:
            if ip in self.authorized_ips:
                return True
            
            if not mac:
                print(f"[FIREWALL][WARNING] No se puede autorizar {ip} sin MAC (anti-spoofing)")
                return False
            
            # Vincular IP+MAC en el firewall 
            rule = f"iptables -I FORWARD -s {ip} -m mac --mac-source {mac} -j ACCEPT"
            if self._run(rule):
                self._run(f"iptables -t nat -I PREROUTING 1 -i {LAN_INTERFACE} -m mac --mac-source {mac} -p udp --dport 53 -j DNAT --to-destination {EXTERNAL_DNS}:53")
                self._run(f"iptables -t nat -I PREROUTING 1 -i {LAN_INTERFACE} -m mac --mac-source {mac} -p tcp --dport 80 -j ACCEPT")
                self._run(f"iptables -t nat -I PREROUTING 1 -i {LAN_INTERFACE} -m mac --mac-source {mac} -p tcp --dport 443 -j ACCEPT")
                self.authorized_ips.add(ip)
                print(f"[FIREWALL] IP autorizada con MAC: {ip} ({mac})")
                return True
            
            print(f"[FIREWALL][ERROR] No se pudo crear regla para {ip}")
            return False
    
    def revoke_ip(self, ip: str, mac: str = None) -> bool:
        with self.lock:
            if ip not in self.authorized_ips:
                return False
            
            if mac:
                self._run(f"iptables -I FORWARD 1 -i {LAN_INTERFACE} -m mac --mac-source {mac} -j DROP")
                self._run(f"conntrack -D -s {ip} 2>/dev/null; conntrack -D -d {ip} 2>/dev/null; true")
                self._run(f"iptables -t nat -D PREROUTING -i {LAN_INTERFACE} -m mac --mac-source {mac} -p udp --dport 53 -j DNAT --to-destination {EXTERNAL_DNS}:53")
                self._run(f"iptables -t nat -D PREROUTING -i {LAN_INTERFACE} -m mac --mac-source {mac} -p tcp --dport 80 -j ACCEPT")
                self._run(f"iptables -t nat -D PREROUTING -i {LAN_INTERFACE} -m mac --mac-source {mac} -p tcp --dport 443 -j ACCEPT")
                
            
            self.authorized_ips.discard(ip)
            print(f"[FIREWALL] IP revocada: {ip}")
            return True
    
    def cleanup(self):
        self._run("iptables -F")
        self._run("iptables -t nat -F")
        self._run("iptables -P FORWARD ACCEPT")
        print("[FIREWALL] Reglas limpiadas")
