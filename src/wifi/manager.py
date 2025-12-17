import subprocess
import os
import signal
import time
import threading
from typing import Optional, List, Dict

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    LAN_INTERFACE, WAN_INTERFACE, WIFI_SSID, WIFI_PASSWORD, WIFI_CHANNEL,
    PORTAL_IP, LAN_NETWORK, DHCP_END, DHCP_START
)


class WiFiManager:
    
    def __init__(self):
        self.interface = LAN_INTERFACE
        self.ssid = WIFI_SSID
        self.password = WIFI_PASSWORD
        self.channel = WIFI_CHANNEL
        self.hostapd_process: Optional[subprocess.Popen] = None
        self._running = False
        self._lock = threading.Lock()
        
        self.hostapd_conf = "/tmp/netguard_hostapd.conf"
    
    def _run(self, cmd: str, check: bool = False) -> tuple[bool, str]:
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
    
    
    def create_hostapd_config(self) -> str:
        config = f"""# NetGuard Hotspot Configuration
interface={self.interface}
driver=nl80211
ssid={self.ssid}
hw_mode=g
channel={self.channel}
ieee80211n=1
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
ap_isolate=1
wpa=2
wpa_passphrase={self.password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
"""
        
        with open(self.hostapd_conf, 'w') as f:
            f.write(config)
        
        return self.hostapd_conf
    
    
    def start_hostapd(self) -> bool:
        """Inicia el servicio hostapd."""
        config_file = self.create_hostapd_config()
        
        # Verificar que hostapd está instalado
        success, _ = self._run("which hostapd")
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
    
    
    def start_hotspot(self) -> bool:
        """Inicia el hotspot WiFi completo."""
        with self._lock:
            if self._running:
                print("[WIFI] Hotspot ya está corriendo")
                return True
            
            print(f"[WIFI] Iniciando hotspot en {self.interface}...")
            
            if not self.start_hostapd():
                self.stop_hotspot()
                return False

            
            self._running = True
            print(f"[WIFI] ✓ Hotspot activo - SSID: {self.ssid}  Contraseña: {self.password}")
            
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
            
            # Matar cualquier proceso restante
            self._run("pkill -9 hostapd 2>/dev/null")
            self._run("pkill -9 -f 'dnsmasq.*netguard' 2>/dev/null")
            
            # Limpiar archivos temporales
            if os.path.exists(self.hostapd_conf):
                os.remove(self.hostapd_conf)
            
            # Bajar interfaz
            self._run(f"ip link set {self.interface} down")
            
            self._running = False
            print("[WIFI] Hotspot detenido")
    
    
    def is_running(self) -> bool:
        """Verifica si el hotspot está corriendo."""
        return self._running and self.hostapd_process and self.hostapd_process.poll() is None

