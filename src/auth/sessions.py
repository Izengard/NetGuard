import time
import threading
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SESSION_TIMEOUT

try:
    from utils.network import get_mac_from_ip
except ImportError:
    get_mac_from_ip = lambda ip: None


class SessionManager:
    
    def __init__(self, firewall_manager):
        self.firewall = firewall_manager
        
        # Sesiones: {ip: {'username': str, 'login_time': float, 'mac': str}}
        self.sessions = {}
        self.lock = threading.Lock()
        self._running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
    
    def _monitor_loop(self):
        while self._running:
            time.sleep(30)
            self._cleanup_expired()
            self._check_mac_spoofing()
    
    def _cleanup_expired(self):
        now = time.time()
        expired = []
        
        with self.lock:
            for ip, data in self.sessions.items():
                if now - data['login_time'] > SESSION_TIMEOUT:
                    expired.append(ip)
        
        for ip in expired:
            self.end_session(ip)
            print(f"[SESSION] Sesión expirada: {ip}")
    
    def _check_mac_spoofing(self):
        spoofed = []
        
        with self.lock:
            for ip, data in self.sessions.items():
                if data.get('mac'):
                    current_mac = get_mac_from_ip(ip)
                    if current_mac and current_mac != data['mac']:
                        print(f"[SECURITY] ¡Spoofing detectado! IP {ip}: "
                              f"MAC original {data['mac']} -> actual {current_mac}")
                        spoofed.append(ip)
        

        for ip in spoofed:
            self.end_session(ip)
            print(f"[SECURITY] Sesión revocada por suplantación: {ip}")
    
    def create_session(self, ip_address: str, username: str) -> bool:
        mac = get_mac_from_ip(ip_address)
        
        # Autorizar en firewall 
        if not self.firewall.authorize_ip(ip_address, mac):
            return False
        
        with self.lock:
            self.sessions[ip_address] = {
                'username': username,
                'login_time': time.time(),
                'mac': mac 
            }
        
        print(f"[SESSION] Nueva sesión: {username}@{ip_address} (MAC: {mac or 'N/A'})")
        return True
    
    def end_session(self, ip_address: str) -> bool:
        mac = None
        with self.lock:
            if ip_address not in self.sessions:
                return False
            mac = self.sessions[ip_address].get('mac')
            del self.sessions[ip_address]
        
        self.firewall.revoke_ip(ip_address, mac)
        print(f"[SESSION] Sesión terminada: {ip_address}")
        return True
    
    def is_authenticated(self, ip_address: str) -> bool:
        with self.lock:
            return ip_address in self.sessions
    
    def get_session(self, ip_address: str) -> dict:
        with self.lock:
            return self.sessions.get(ip_address)
    
    def stop(self):
        self._running = False
        with self.lock:
            ips = list(self.sessions.keys())
        for ip in ips:
            self.end_session(ip)
