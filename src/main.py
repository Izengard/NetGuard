"""
NetGuard - Portal Cautivo
Punto de entrada principal.

Uso:
    sudo python3 main.py [opciones]
    
Opciones:
    --no-firewall    No inicializar reglas de firewall (para pruebas)
    --no-dns         No iniciar servidor DNS
    --add-user       Modo para agregar usuarios
    --wifi           Usar interfaz WiFi como hotspot
    --wifi-only      Solo iniciar hotspot WiFi (sin servidor HTTP)
"""
import sys
import os
import signal
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PORTAL_IP, PORTAL_PORT, WIFI_INTERFACE, WIFI_SSID, LAN_INTERFACE
from firewall.manager import FirewallManager
from auth.users import UserManager
from auth.sessions import SessionManager
from http_server.server import CaptivePortalServer

# Variables globales para cleanup
firewall = None
session_manager = None
http_server = None
dns_server = None
wifi_manager = None


def signal_handler(sig, frame):
    print("\n[MAIN] Cerrando portal cautivo...")
    cleanup()
    sys.exit(0)


def cleanup():
    """Limpia recursos al cerrar."""
    global http_server, session_manager, firewall, dns_server, wifi_manager
    
    if dns_server:
        dns_server.stop()
    if http_server:
        http_server.stop()
    if session_manager:
        session_manager.stop()
    if firewall:
        firewall.cleanup()
    if wifi_manager:
        wifi_manager.stop_hotspot()


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
    global firewall, session_manager, http_server, dns_server, wifi_manager
    
    # Parsear argumentos
    parser = argparse.ArgumentParser(description='NetGuard - Portal Cautivo')
    parser.add_argument('--no-firewall', action='store_true', help='No inicializar firewall')
    parser.add_argument('--no-dns', action='store_true', help='No iniciar servidor DNS')
    parser.add_argument('--add-user', action='store_true', help='Agregar usuario')
    parser.add_argument('--wifi', action='store_true', help='Usar WiFi hotspot como interfaz LAN')
    parser.add_argument('--wifi-only', action='store_true', help='Solo iniciar hotspot WiFi')
    parser.add_argument('--wifi-interface', type=str, help='Interfaz WiFi a usar (default: wlan0)')
    parser.add_argument('--wifi-ssid', type=str, help='SSID del hotspot WiFi')
    parser.add_argument('--wifi-password', type=str, help='Contraseña del hotspot WiFi')
    args = parser.parse_args()
    
    # Modo agregar usuario
    if args.add_user:
        add_user_mode()
        return
    
    # Banner
    print("=" * 50)
    print("     NETGUARD - Portal Cautivo")
    if args.wifi or args.wifi_only:
        print("        [Modo WiFi Hotspot]")
    print("=" * 50)
    
    # Verificar root 
    if sys.platform.startswith('linux') and not args.no_firewall:
        if os.geteuid() != 0:
            print("[ERROR] Se requieren privilegios de root (sudo)")
            sys.exit(1)
    
    # Registrar señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Iniciar WiFi Hotspot si se solicita
    if args.wifi or args.wifi_only:
        print("\n[1/5] Iniciando WiFi Hotspot...")
        try:
            from wifi.manager import WiFiManager
            import config
            
            # Aplicar argumentos de línea de comandos a la configuración
            if args.wifi_interface:
                config.WIFI_INTERFACE = args.wifi_interface
            if args.wifi_ssid:
                config.WIFI_SSID = args.wifi_ssid
            if args.wifi_password:
                config.WIFI_PASSWORD = args.wifi_password
            
            # Actualizar LAN_INTERFACE para usar WiFi
            config.LAN_INTERFACE = config.WIFI_INTERFACE
            
            wifi_manager = WiFiManager()
            if wifi_manager.start_hotspot():
                print(f"[WIFI] ✓ Hotspot activo: {config.WIFI_SSID}")
            else:
                print("[ERROR] No se pudo iniciar el hotspot WiFi")
                print("        Verifica que la interfaz WiFi existe y soporta modo AP")
                print("        Intenta ejecutar: sudo ./scripts/setup_wifi_hotspot.sh")
                if args.wifi_only:
                    sys.exit(1)
                print("        Continuando sin hotspot...")
                wifi_manager = None
        except ImportError as e:
            print(f"[ERROR] No se pudo cargar módulo WiFi: {e}")
            if args.wifi_only:
                sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Error iniciando hotspot: {e}")
            if args.wifi_only:
                sys.exit(1)
        
        # Si solo queremos el hotspot, quedarnos aquí
        if args.wifi_only:
            print("\n" + "=" * 50)
            print(f"Hotspot WiFi activo: {config.WIFI_SSID}")
            print("Presiona Ctrl+C para detener")
            print("=" * 50 + "\n")
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                cleanup()
            return
        
        step_offset = 1
    else:
        step_offset = 0
    
    # Inicializar componentes
    print(f"\n[{1+step_offset}/4] Inicializando firewall...")
    firewall = FirewallManager()
    if not args.no_firewall:
        firewall.initialize_rules()
    else:
        print("      (modo sin firewall)")
    
    print(f"[{2+step_offset}/4] Cargando usuarios...")
    user_manager = UserManager()
    
    print(f"[{3+step_offset}/4] Iniciando gestor de sesiones...")
    session_manager = SessionManager(firewall)
    
    # Servidor DNS (opcional)
    if not args.no_dns:
        print(f"[{3+step_offset}.5/4] Iniciando servidor DNS...")
        try:
            from dns.dns_server import CaptivePortalDNS
            dns_server = CaptivePortalDNS(PORTAL_IP)
            dns_server.start()
        except Exception as e:
            print(f"      DNS no disponible: {e}")
    
    print(f"[{4+step_offset}/4] Iniciando servidor HTTP...")
    http_server = CaptivePortalServer(session_manager, user_manager)
    
    print("\n" + "=" * 50)
    print(f"Portal activo en: http://{PORTAL_IP}:{PORTAL_PORT}")
    if wifi_manager and wifi_manager.is_running():
        from config import WIFI_SSID, WIFI_PASSWORD
        print(f"WiFi Hotspot: {WIFI_SSID}")
        if WIFI_PASSWORD and len(WIFI_PASSWORD) >= 8:
            print(f"Contraseña WiFi: {WIFI_PASSWORD}")
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
