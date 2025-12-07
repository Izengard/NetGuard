"""
NetGuard - Portal Cautivo
Punto de entrada principal.

Uso:
    sudo python3 main.py [opciones]
    
Opciones:
    --no-firewall    No inicializar reglas de firewall (para pruebas)
    --no-dns         No iniciar servidor DNS
    --add-user       Modo para agregar usuarios
"""
import sys
import os
import signal
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PORTAL_IP, PORTAL_PORT
from firewall.manager import FirewallManager
from auth.users import UserManager
from auth.sessions import SessionManager
from http_server.server import CaptivePortalServer

# Variables globales para cleanup
firewall = None
session_manager = None
http_server = None
dns_server = None


def signal_handler(sig, frame):
    print("\n[MAIN] Cerrando portal cautivo...")
    cleanup()
    sys.exit(0)


def cleanup():
    """Limpia recursos al cerrar."""
    global http_server, session_manager, firewall, dns_server
    
    if dns_server:
        dns_server.stop()
    if http_server:
        http_server.stop()
    if session_manager:
        session_manager.stop()
    if firewall:
        firewall.cleanup()


def add_user_mode():
    users = UserManager()
    print("\n=== Agregar Usuario ===")
    username = input("Usuario: ").strip()
    password = input("Contraseña: ").strip()
    
    if username and password:
        if users.add_user(username, password):
            print(f"Usuario '{username}' creado exitosamente.")
        else:
            print(f"Error: El usuario '{username}' ya existe.")
    else:
        print("Error: Usuario y contraseña requeridos.")


def main():
    global firewall, session_manager, http_server, dns_server
    
    # Parsear argumentos
    parser = argparse.ArgumentParser(description='NetGuard - Portal Cautivo')
    parser.add_argument('--no-firewall', action='store_true', help='No inicializar firewall')
    parser.add_argument('--no-dns', action='store_true', help='No iniciar servidor DNS')
    parser.add_argument('--add-user', action='store_true', help='Agregar usuario')
    args = parser.parse_args()
    
    # Modo agregar usuario
    if args.add_user:
        add_user_mode()
        return
    
    # Banner
    print("=" * 50)
    print("     NETGUARD - Portal Cautivo")
    print("=" * 50)
    
    # Verificar root 
    if sys.platform.startswith('linux') and not args.no_firewall:
        if os.geteuid() != 0:
            print("[ERROR] Se requieren privilegios de root (sudo)")
            sys.exit(1)
    
    # Registrar señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Inicializar componentes
    print("\n[1/4] Inicializando firewall...")
    firewall = FirewallManager()
    if not args.no_firewall:
        firewall.initialize_rules()
    else:
        print("      (modo sin firewall)")
    
    print("[2/4] Cargando usuarios...")
    user_manager = UserManager()
    
    print("[3/4] Iniciando gestor de sesiones...")
    session_manager = SessionManager(firewall)
    
    # Servidor DNS (opcional)
    if not args.no_dns:
        print("[3.5/4] Iniciando servidor DNS...")
        try:
            from dns.dns_server import CaptivePortalDNS
            dns_server = CaptivePortalDNS(PORTAL_IP)
            dns_server.start()
        except Exception as e:
            print(f"      DNS no disponible: {e}")
    
    print("[4/4] Iniciando servidor HTTP...")
    http_server = CaptivePortalServer(session_manager, user_manager)
    
    print("\n" + "=" * 50)
    print(f"Portal activo en: http://{PORTAL_IP}:{PORTAL_PORT}")
    print("Presiona Ctrl+C para detener")
    print("=" * 50 + "\n")
    
    # Iniciar servidor (bloqueante)
    try:
        http_server.start()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
