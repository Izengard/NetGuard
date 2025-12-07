import urllib.parse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CAPTIVE_DETECTION_PATHS, PORTAL_IP, PORTAL_PORT,TEMPLATES_DIR


def load_template(name: str) -> str:
    template_path = os.path.join(TEMPLATES_DIR, name)
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"<html><body><h1>Error: Template '{name}' not found</h1></body></html>"
    except Exception as e:
        return f"<html><body><h1>Error loading template: {e}</h1></body></html>"


class RequestHandler:
    
    def __init__(self, session_manager, user_manager, client_ip: str):
        self.session_manager = session_manager
        self.user_manager = user_manager
        self.client_ip = client_ip
    
    def handle_request(self, raw_request: str) -> str:
        method, path, body = self._parse_request(raw_request)
        
        # Deteccion de portal cautivo 
        if path in CAPTIVE_DETECTION_PATHS:
            return self._redirect(f"http://{PORTAL_IP}:{PORTAL_PORT}/login")
        
        
        if path == '/login':
            if method == 'POST':
                return self._handle_login(body)
            template = load_template('login.html')
            return self._response(200, template.format(error=""))
        
        if path == '/logout':
            self.session_manager.end_session(self.client_ip)
            return self._redirect('/login')
        
        if path == '/status':
            session = self.session_manager.get_session(self.client_ip)
            if session:
                template = load_template('status.html')
                return self._response(200, template.format(username=session['username']))
            return self._redirect('/login')
        
        # Ruta por defecto
        if self.session_manager.is_authenticated(self.client_ip):
            return self._redirect('/status')
        return self._redirect('/login')
    
    def _handle_login(self, body: str) -> str:
        params = urllib.parse.parse_qs(body)
        username = params.get('username', [''])[0]
        password = params.get('password', [''])[0]
        
        if self.user_manager.authenticate(username, password):
            self.session_manager.create_session(self.client_ip, username)
            print(f"[AUTH] Login exitoso: {username}@{self.client_ip}")
            return self._redirect('/status')
        
        print(f"[AUTH] Login fallido: {username}@{self.client_ip}")
        template = load_template('login.html')
        error = '<p class="error">Usuario o contrasena incorrectos</p>'
        return self._response(200, template.format(error=error))
    
    def _parse_request(self, raw_request: str) -> tuple:
        parts = raw_request.split('\r\n\r\n', 1)
        header_section = parts[0]
        body = parts[1] if len(parts) > 1 else ''
        
        lines = header_section.split('\r\n')
        request_line = lines[0].split(' ') if lines else []
        
        method = request_line[0] if len(request_line) > 0 else 'GET'
        path = request_line[1].split('?')[0] if len(request_line) > 1 else '/'
        
        return method, path, body
    
    def _response(self, status_code: int, body: str, content_type: str = 'text/html') -> str:
        status_text = {200: 'OK', 302: 'Found', 404: 'Not Found'}.get(status_code, 'OK')
        body_bytes = body.encode('utf-8')
        headers = [
            f"HTTP/1.1 {status_code} {status_text}",
            f"Content-Type: {content_type}; charset=utf-8",
            f"Content-Length: {len(body_bytes)}",
            "Connection: close",
            "Cache-Control: no-cache, no-store",
        ]
        return '\r\n'.join(headers) + '\r\n\r\n' + body
    
    def _redirect(self, location: str) -> str:
        body = f'<html><body>Redirigiendo a <a href="{location}">{location}</a></body></html>'
        headers = [
            "HTTP/1.1 302 Found",
            f"Location: {location}",
            f"Content-Length: {len(body.encode('utf-8'))}",
            "Connection: close",
            "Cache-Control: no-cache, no-store",
        ]
        return '\r\n'.join(headers) + '\r\n\r\n' + body
