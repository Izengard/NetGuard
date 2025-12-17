"""
NetGuard - Portal Cautivo
Punto de entrada principal.

Uso:
    sudo python3 main.py [opciones]
    
Opciones:
    --add-user       Modo para agregar usuarios
"""
import sys
import os
import signal
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from firewall.manager import FirewallManager
from auth.users import UserManager
from auth.sessions import SessionManager
from http_server.server import CaptivePortalServer
from gateway.preconfig import apply_gateway_preconfig


# Variables globales para cleanup
firewall = None
session_manager = None
http_server = None
wifi_manager = None



def signal_handler(sig, frame):
    print("\n[MAIN] Cerrando portal cautivo...")
    cleanup()
    sys.exit(0)


def cleanup():
    """Limpia recursos al cerrar."""
    global http_server, session_manager, firewall, wifi_manager
    
    
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
    global firewall, session_manager, http_server, wifi_manager
    
    # Parsear argumentos
    parser = argparse.ArgumentParser(description='NetGuard - Portal Cautivo')
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
    if sys.platform.startswith('linux'):
        if os.geteuid() != 0:
            print("[ERROR] Se requieren privilegios de root (sudo)")
            sys.exit(1)
    
    # Registrar señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Aplicar preconfiguración del gateway
    ok, msg = apply_gateway_preconfig()
    if not ok:
        return print(f"[ERROR] Error de Preconfiguración : {msg}")
    
    # Auto-detect if LAN interface is a WiFi interface (common Linux names)
    lan_iface = config.LAN_INTERFACE or ""
    wifi_prefixes = ('wlp', 'wlx', 'wlan', 'wl', 'wifi', 'ath', 'ra')
    is_wifi = any(lan_iface.startswith(p) for p in wifi_prefixes) or 'wl' in lan_iface

    if is_wifi:
        print("Interfaz LAN detectada como WiFi, iniciando WiFi Hotspot...")
        try:
            from wifi.manager import WiFiManager

            wifi_manager = WiFiManager()
            if wifi_manager.start_hotspot():
                print(f"[WIFI] ✓ Hotspot activo: {config.WIFI_SSID}")
            else:
                print("[ERROR] No se pudo iniciar el hotspot WiFi")
                print("        Verifica que la interfaz WiFi existe y soporta modo AP")
                print("        Intenta ejecutar: sudo ./scripts/setup_wifi_hotspot.sh")
                sys.exit(1)
        except ImportError as e:
            print(f"[ERROR] No se pudo cargar módulo WiFi: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Error iniciando hotspot: {e}")
            sys.exit(1)

        step_offset = 1
    else:
        step_offset = 0
    
    # Inicializar componentes
    print(f"\n[{1+step_offset}/4] Inicializando firewall...")
    firewall = FirewallManager()
    firewall.initialize_rules()
    
    print(f"[{2+step_offset}/4] Cargando usuarios...")
    user_manager = UserManager()
    
    print(f"[{3+step_offset}/4] Iniciando gestor de sesiones...")
    session_manager = SessionManager(firewall)
    
    print(f"[{4+step_offset}/4] Iniciando servidor HTTP...")
    http_server = CaptivePortalServer(session_manager, user_manager)
    
    print(f"\n" + "=" * 50)
    print(f"Portal activo en: http://{config.PORTAL_IP}:{config.PORTAL_PORT}")
    if wifi_manager and wifi_manager.is_running():
        print(f"WiFi Hotspot: {config.WIFI_SSID}")
        if config.WIFI_PASSWORD and len(config.WIFI_PASSWORD) >= 8:
            print(f"Contraseña WiFi: {config.WIFI_PASSWORD}")
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
