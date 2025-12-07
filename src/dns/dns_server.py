import socket
import threading
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PORTAL_IP

class CaptivePortalDNS:
       
    def __init__(self, portal_ip: str = None, port: int = 53):
        self.portal_ip = portal_ip or PORTAL_IP
        self.port = port
        self.socket = None
        self.running = False
    
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.settimeout(1.0)
        
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        print(f"[DNS] Servidor iniciado, redirigiendo a {self.portal_ip}")
    
    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
    
    def _loop(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(512)
                response = self._build_response(data)
                if response:
                    self.socket.sendto(response, addr)
            except socket.timeout:
                continue
            except:
                pass
    
    def _build_response(self, query: bytes) -> Optional[bytes]:
        if len(query) < 12:
            return None
        
        try:
            # Header: ID + flags + counts
            response = query[:2]  # Copiar ID
            response += b'\x81\x80'  # Flags: respuesta estándar
            response += b'\x00\x01\x00\x01\x00\x00\x00\x00'  # Counts
            
            # Copiar pregunta original
            qend = 12
            while query[qend] != 0:
                qend += 1
            qend += 5
            response += query[12:qend]
            
            # Respuesta: puntero + tipo A + clase IN + TTL + IP
            response += b'\xc0\x0c'  # Puntero al nombre
            response += b'\x00\x01\x00\x01'  # Tipo A, Clase IN
            response += b'\x00\x00\x00\x3c'  # TTL 60s
            response += b'\x00\x04'  # Longitud IP
            response += bytes(int(x) for x in self.portal_ip.split('.'))
            
            return response
        except:
            return None
