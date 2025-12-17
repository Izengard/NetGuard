import os
import subprocess
import shutil
import time
from typing import Tuple

import config

DNSMASQ_CONF_PATH = "/etc/dnsmasq.d/netguard-wifi.conf"


def _run(cmd, shell=False):
    try:
        return subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    except Exception as exc:
        class R:
            returncode = 1
            stdout = ""
            stderr = str(exc)

        return R()


def check_interface(iface: str) -> bool:
    if not iface:
        return False
    r = _run(["ip", "link", "show", iface])
    return r.returncode == 0


def stop_conflicting_services() -> None:
    if shutil.which("systemctl"):
        for svc in ("NetworkManager", "wpa_supplicant", "hostapd", "dnsmasq"):
            _run(["systemctl", "stop", svc])
    else:
        _run(["pkill", "-9", "wpa_supplicant"])
        _run(["pkill", "-9", "NetworkManager"])


def disable_systemd_resolved() -> None:
    _run(["systemctl", "stop", "systemd-resolved"])
    _run(["systemctl", "disable", "systemd-resolved"])
    _run(["systemctl", "mask", "systemd-resolved"])

        

def enable_ip_forwarding() -> None:
    try:
        with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
            f.write("1\n")
    except Exception:
        _run(["sysctl", "-w", "net.ipv4.ip_forward=1"])


def set_interface_ip(iface: str, ip: str) -> bool:
    if not iface or not ip:
        return False
    _run(["ip", "link", "set", iface, "down"])  # best-effort
    _run(["ip", "addr", "flush", "dev", iface])
    r = _run(["ip", "addr", "add", f"{ip}/24", "dev", iface])
    if r.returncode != 0:
        return False
    _run(["ip", "link", "set", iface, "up"])
    return True


def create_dnsmasq_config(interface: str, portal_ip: str,
                          dhcp_start: str, dhcp_end: str,
                          path: str = DNSMASQ_CONF_PATH) -> str:
    cfg = f"""# NetGuard WiFi DHCP Configuration
interface={interface}
bind-interfaces
except-interface=lo

listen-address={portal_ip}

no-resolv
no-poll
no-hosts

server=8.8.8.8
server=8.8.4.4

dhcp-range={dhcp_start},{dhcp_end},12h
dhcp-option=option:router,{portal_ip}
dhcp-option=option:dns-server,{portal_ip}
dhcp-authoritative

filter-AAAA

address=/#/{portal_ip}

log-queries
log-dhcp
"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(cfg)
    except Exception:
        pass
    return path


def start_dnsmasq(conf_path: str):
    
    try:
        proc = subprocess.Popen(["dnsmasq", "-C", conf_path, "-d"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        time.sleep(1)
        if proc.poll() is not None:
            _, stderr = proc.communicate(timeout=1)
            return False, stderr.decode(errors="ignore")
        return True, proc
    except Exception as e:
        return False, str(e)


def apply_gateway_preconfig() -> Tuple[bool, str]:
    if os.geteuid() != 0:
        return False, "privilegios root requeridos"

    lan = getattr(config, "LAN_INTERFACE", "")
    wan = getattr(config, "WAN_INTERFACE", "")
    portal_ip = getattr(config, "PORTAL_IP", "192.168.100.1")
    dhcp_start = getattr(config, "DHCP_START", "192.168.100.100")
    dhcp_end = getattr(config, "DHCP_END", "192.168.100.150")

    if not check_interface(lan):
        return False, f"interfaz LAN no encontrada: {lan}"
    if wan and not check_interface(wan):
        return False, f"interfaz WAN no encontrada: {wan}"

    stop_conflicting_services()
    disable_systemd_resolved()
    set_interface_ip(lan, portal_ip)
    enable_ip_forwarding()

    conf_path = create_dnsmasq_config(lan, portal_ip, dhcp_start, dhcp_end)
    dns_ok = start_dnsmasq(conf_path)

    return True, f"[LOG] Gateway Setup Config Completed"
