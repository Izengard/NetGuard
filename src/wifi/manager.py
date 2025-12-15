"""
NetGuard - WiFi Manager
Gestión de interfaces WiFi y modo Access Point (Hotspot).
"""
import subprocess
import os
import signal
import time
import threading
from typing import Optional, List, Dict

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    WIFI_INTERFACE, WIFI_SSID, WIFI_PASSWORD, WIFI_CHANNEL,
    PORTAL_IP, LAN_NETWORK
)


class WiFiManager:
    """Gestiona la interfaz WiFi en modo Access Point (Hotspot)."""
    
    def __init__(self):
        self.interface = WIFI_INTERFACE
        self.ssid = WIFI_SSID
        self.password = WIFI_PASSWORD
        self.channel = WIFI_CHANNEL
        self.hostapd_process: Optional[subprocess.Popen] = None
        self.dnsmasq_process: Optional[subprocess.Popen] = None
        self._running = False
        self._lock = threading.Lock()
        
        # Archivos de configuración temporales
        self.hostapd_conf = "/tmp/netguard_hostapd.conf"
        self.dnsmasq_conf = "/tmp/netguard_dnsmasq_wifi.conf"
    
    def _run_cmd(self, cmd: str, check: bool = False) -> tuple[bool, str]:
        """Ejecuta un comando shell."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            if check and not success:
                print(f"[WIFI] Error en comando: {cmd}")
                print(f"       {output}")
            return success, output
        except Exception as e:
            return False, str(e)
    
    def check_interface(self) -> bool:
        """Verifica que la interfaz WiFi existe y soporta AP mode."""
        # Verificar que existe la interfaz
        success, output = self._run_cmd(f"ip link show {self.interface}")
        if not success:
            print(f"[WIFI] Interfaz {self.interface} no encontrada")
            return False
        
        # Verificar soporte AP mode con iw
        success, output = self._run_cmd(f"iw list 2>/dev/null | grep -A 10 'Supported interface modes' | grep '\\* AP'")
        if not success:
            print(f"[WIFI] Advertencia: No se pudo verificar soporte AP mode")
            # Continuar de todos modos, algunos drivers no reportan correctamente
        
        return True
    
    def get_wifi_interfaces(self) -> List[str]:
        """Lista las interfaces WiFi disponibles."""
        interfaces = []
        success, output = self._run_cmd("iw dev 2>/dev/null | grep Interface | awk '{print $2}'")
        if success and output.strip():
            interfaces = output.strip().split('\n')
        
        # Método alternativo si iw no está disponible
        if not interfaces:
            success, output = self._run_cmd("ls /sys/class/net/ | xargs -I{} sh -c 'test -d /sys/class/net/{}/wireless && echo {}'")
            if success and output.strip():
                interfaces = output.strip().split('\n')
        
        return [i for i in interfaces if i]  # Filtrar vacíos
    
    def stop_conflicting_services(self) -> bool:
        """Detiene servicios que pueden interferir con el hotspot."""
        services = [
            "NetworkManager",
            "wpa_supplicant", 
            "hostapd",
            "dnsmasq"
        ]
        
        for service in services:
            # Intentar con systemctl primero
            self._run_cmd(f"systemctl stop {service} 2>/dev/null")
            # Matar procesos directamente si es necesario
            self._run_cmd(f"pkill -9 {service} 2>/dev/null")
        
        # Matar cualquier proceso usando la interfaz
        self._run_cmd(f"pkill -f 'hostapd.*{self.interface}' 2>/dev/null")
        
        time.sleep(1)
        return True
    
    def configure_interface(self) -> bool:
        """Configura la interfaz WiFi con IP estática."""
        commands = [
            # Bajar la interfaz
            f"ip link set {self.interface} down",
            # Limpiar IPs existentes
            f"ip addr flush dev {self.interface}",
            # Configurar modo (algunos drivers lo necesitan)
            f"iw dev {self.interface} set type __ap 2>/dev/null || true",
            # Subir la interfaz
            f"ip link set {self.interface} up",
            # Asignar IP
            f"ip addr add {PORTAL_IP}/24 dev {self.interface}",
        ]
        
        for cmd in commands:
            success, _ = self._run_cmd(cmd)
            # Continuar incluso si algunos fallan (set type puede fallar)
        
        # Verificar que la IP se asignó
        success, output = self._run_cmd(f"ip addr show {self.interface} | grep {PORTAL_IP}")
        if not success:
            print(f"[WIFI] Error: No se pudo asignar IP {PORTAL_IP} a {self.interface}")
            return False
        
        print(f"[WIFI] Interfaz {self.interface} configurada con IP {PORTAL_IP}")
        return True
    
    def create_hostapd_config(self) -> str:
        """Genera el archivo de configuración de hostapd."""
        config = f"""# NetGuard Hotspot Configuration
interface={self.interface}
driver=nl80211
ssid={self.ssid}
hw_mode=g
channel={self.channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={self.password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
        
        # Si la contraseña está vacía, crear red abierta
        if not self.password or len(self.password) < 8:
            config = f"""# NetGuard Hotspot Configuration (Open Network)
interface={self.interface}
driver=nl80211
ssid={self.ssid}
hw_mode=g
channel={self.channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        
        with open(self.hostapd_conf, 'w') as f:
            f.write(config)
        
        return self.hostapd_conf
    
    def create_dnsmasq_config(self) -> str:
        """Genera el archivo de configuración de dnsmasq para el hotspot."""
        # Extraer rango DHCP de la red
        network_base = PORTAL_IP.rsplit('.', 1)[0]
        dhcp_start = f"{network_base}.100"
        dhcp_end = f"{network_base}.200"
        
        config = f"""# NetGuard WiFi DHCP Configuration
interface={self.interface}
bind-interfaces
port=0
dhcp-range={dhcp_start},{dhcp_end},12h
dhcp-option=option:router,{PORTAL_IP}
dhcp-option=option:dns-server,{PORTAL_IP}
dhcp-authoritative
log-queries
log-dhcp
"""
        
        with open(self.dnsmasq_conf, 'w') as f:
            f.write(config)
        
        return self.dnsmasq_conf
    
    def start_hostapd(self) -> bool:
        """Inicia el servicio hostapd."""
        config_file = self.create_hostapd_config()
        
        # Verificar que hostapd está instalado
        success, _ = self._run_cmd("which hostapd")
        if not success:
            print("[WIFI] Error: hostapd no está instalado")
            print("       Instalar con: apt-get install hostapd")
            return False
        
        try:
            # Iniciar hostapd en background
            self.hostapd_process = subprocess.Popen(
                ["hostapd", config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Esperar un momento para verificar que inició
            time.sleep(2)
            
            if self.hostapd_process.poll() is not None:
                # El proceso terminó, algo falló
                _, stderr = self.hostapd_process.communicate()
                print(f"[WIFI] Error iniciando hostapd: {stderr.decode()}")
                return False
            
            print(f"[WIFI] hostapd iniciado - SSID: {self.ssid}")
            return True
            
        except Exception as e:
            print(f"[WIFI] Excepción iniciando hostapd: {e}")
            return False
    
    def start_dnsmasq(self) -> bool:
        """Inicia el servicio dnsmasq para DHCP."""
        config_file = self.create_dnsmasq_config()
        
        # Verificar que dnsmasq está instalado
        success, _ = self._run_cmd("which dnsmasq")
        if not success:
            print("[WIFI] Error: dnsmasq no está instalado")
            print("       Instalar con: apt-get install dnsmasq")
            return False
        
        try:
            self.dnsmasq_process = subprocess.Popen(
                ["dnsmasq", "-C", config_file, "-d"],  # -d = no daemon
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(1)
            
            if self.dnsmasq_process.poll() is not None:
                _, stderr = self.dnsmasq_process.communicate()
                print(f"[WIFI] Error iniciando dnsmasq: {stderr.decode()}")
                return False
            
            print(f"[WIFI] dnsmasq iniciado - DHCP activo")
            return True
            
        except Exception as e:
            print(f"[WIFI] Excepción iniciando dnsmasq: {e}")
            return False
    
    def start_hotspot(self) -> bool:
        """Inicia el hotspot WiFi completo."""
        with self._lock:
            if self._running:
                print("[WIFI] Hotspot ya está corriendo")
                return True
            
            print(f"[WIFI] Iniciando hotspot en {self.interface}...")
            
            # 1. Verificar interfaz
            if not self.check_interface():
                return False
            
            # 2. Detener servicios conflictivos
            print("[WIFI] Deteniendo servicios conflictivos...")
            self.stop_conflicting_services()
            
            # 3. Configurar interfaz
            print("[WIFI] Configurando interfaz...")
            if not self.configure_interface():
                return False
            
            # 4. Iniciar hostapd
            print("[WIFI] Iniciando Access Point...")
            if not self.start_hostapd():
                self.stop_hotspot()
                return False
            
            # 5. Iniciar DHCP
            print("[WIFI] Iniciando servidor DHCP...")
            if not self.start_dnsmasq():
                self.stop_hotspot()
                return False
            
            self._running = True
            print(f"[WIFI] ✓ Hotspot activo - SSID: {self.ssid}")
            if self.password and len(self.password) >= 8:
                print(f"[WIFI]   Contraseña: {self.password}")
            else:
                print(f"[WIFI]   Red abierta (sin contraseña)")
            
            return True
    
    def stop_hotspot(self):
        """Detiene el hotspot WiFi."""
        with self._lock:
            print("[WIFI] Deteniendo hotspot...")
            
            # Detener procesos
            if self.hostapd_process:
                try:
                    self.hostapd_process.terminate()
                    self.hostapd_process.wait(timeout=5)
                except:
                    self.hostapd_process.kill()
                self.hostapd_process = None
            
            if self.dnsmasq_process:
                try:
                    self.dnsmasq_process.terminate()
                    self.dnsmasq_process.wait(timeout=5)
                except:
                    self.dnsmasq_process.kill()
                self.dnsmasq_process = None
            
            # Matar cualquier proceso restante
            self._run_cmd("pkill -9 hostapd 2>/dev/null")
            self._run_cmd("pkill -9 -f 'dnsmasq.*netguard' 2>/dev/null")
            
            # Limpiar archivos temporales
            for f in [self.hostapd_conf, self.dnsmasq_conf]:
                if os.path.exists(f):
                    os.remove(f)
            
            # Bajar interfaz
            self._run_cmd(f"ip link set {self.interface} down")
            
            self._running = False
            print("[WIFI] Hotspot detenido")
    
    def get_connected_clients(self) -> List[Dict]:
        """Obtiene lista de clientes conectados al hotspot."""
        clients = []
        
        # Obtener clientes de hostapd
        success, output = self._run_cmd(f"iw dev {self.interface} station dump")
        if success and output:
            current_mac = None
            for line in output.split('\n'):
                if 'Station' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        current_mac = parts[1]
                        clients.append({'mac': current_mac, 'ip': None})
        
        # Obtener IPs del ARP
        success, output = self._run_cmd("cat /proc/net/arp")
        if success:
            for line in output.split('\n')[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 6:
                    ip = parts[0]
                    mac = parts[3].upper()
                    # Actualizar cliente con IP
                    for client in clients:
                        if client['mac'].upper() == mac:
                            client['ip'] = ip
                            break
        
        return clients
    
    def is_running(self) -> bool:
        """Verifica si el hotspot está corriendo."""
        return self._running and self.hostapd_process and self.hostapd_process.poll() is None


class WiFiClient:
    """Gestiona conexiones WiFi como cliente."""
    
    def __init__(self, interface: str = None):
        self.interface = interface or WIFI_INTERFACE
    
    def _run_cmd(self, cmd: str) -> tuple[bool, str]:
        """Ejecuta un comando shell."""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def scan_networks(self) -> List[Dict]:
        """Escanea redes WiFi disponibles."""
        networks = []
        
        # Asegurar que la interfaz está arriba
        self._run_cmd(f"ip link set {self.interface} up")
        
        # Escanear con iw
        success, output = self._run_cmd(f"iw dev {self.interface} scan 2>/dev/null")
        if success:
            current = {}
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('BSS '):
                    if current:
                        networks.append(current)
                    current = {'bssid': line.split()[1].replace('(', '').replace(')', '')}
                elif 'SSID:' in line:
                    current['ssid'] = line.split('SSID:', 1)[1].strip()
                elif 'signal:' in line:
                    current['signal'] = line.split('signal:', 1)[1].strip()
                elif 'capability:' in line:
                    current['encrypted'] = 'Privacy' in line
            if current:
                networks.append(current)
        
        return networks
    
    def connect(self, ssid: str, password: str = None) -> bool:
        """Conecta a una red WiFi."""
        # Método básico usando wpa_supplicant
        config = f"""
network={{
    ssid="{ssid}"
    {"psk=\"" + password + "\"" if password else "key_mgmt=NONE"}
}}
"""
        config_file = "/tmp/netguard_wpa.conf"
        with open(config_file, 'w') as f:
            f.write(config)
        
        # Detener wpa_supplicant existente
        self._run_cmd("pkill wpa_supplicant")
        time.sleep(1)
        
        # Conectar
        success, _ = self._run_cmd(
            f"wpa_supplicant -B -i {self.interface} -c {config_file}"
        )
        
        if success:
            # Obtener IP con DHCP
            time.sleep(2)
            self._run_cmd(f"dhclient {self.interface}")
            print(f"[WIFI] Conectado a {ssid}")
            return True
        
        print(f"[WIFI] Error conectando a {ssid}")
        return False
    
    def disconnect(self):
        """Desconecta de la red WiFi actual."""
        self._run_cmd("pkill wpa_supplicant")
        self._run_cmd(f"ip addr flush dev {self.interface}")
        print("[WIFI] Desconectado")
