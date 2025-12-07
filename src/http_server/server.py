import socket
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PORTAL_IP, PORTAL_PORT, BUFFER_SIZE, SOCKET_TIMEOUT
from http_server.handlers import RequestHandler


class CaptivePortalServer:
    
    def __init__(self, session_manager, user_manager):
        self.session_manager = session_manager
        self.user_manager = user_manager
        self.server_socket = None
        self.running = False
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((PORTAL_IP, PORTAL_PORT))
        self.server_socket.listen()
        
        self.running = True
        print(f"[HTTP] Servidor iniciado en http://{PORTAL_IP}:{PORTAL_PORT}")
        
        self._accept_loop()
    
    def _accept_loop(self):
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, client_address = self.server_socket.accept()
                
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[HTTP] Error aceptando conexión: {e}")
    
    def _handle_client(self, client_socket, client_address):
        try:
            client_socket.settimeout(SOCKET_TIMEOUT)
            
            request_data = client_socket.recv(BUFFER_SIZE).decode('utf-8', errors='ignore')
            if not request_data:
                return
            
            handler = RequestHandler(
                self.session_manager,
                self.user_manager,
                client_address[0]
            )
            response = handler.handle_request(request_data)      
            client_socket.sendall(response.encode('utf-8'))
            
        except Exception as e:
            print(f"[HTTP] Error manejando cliente {client_address}: {e}")
        finally:
            client_socket.close()
    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[HTTP] Servidor detenido")
