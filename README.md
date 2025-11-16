# NetGuard - Portal Cautivo

Portal cautivo completo implementado en Python (stdlib only) y bash para control de acceso a red en sistemas Unix.

## 🎯 Características

- ✅ Servidor HTTP de autenticación
- ✅ Control de acceso mediante iptables
- ✅ Gestión de usuarios y sesiones
- ✅ Soporte multi-usuario concurrente (multithreading)
- ✅ Expiración automática de sesiones
- ✅ Interfaz web
- ✅ Sin dependencias externas (solo stdlib de Python)

## 📋 Requisitos

### Software

- Linux (Ubuntu 20.04+ / Debian 11+ recomendado)
- Python 3.7+
- iptables
- dnsmasq (DHCP/DNS server)
- Acceso root

## 🚀 Instalación

### 1. Preparar el Sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y python3 iptables dnsmasq net-tools git

# Clonar o copiar archivos del proyecto
cd /opt
sudo mkdir netguard
cd netguard
# Copiar archivos

```

### 2. Configurar Interfaces de Red

Editar `/etc/netplan/01-netcfg.yaml` o el archivo de configuración de red correspondiente:

```yaml
network:
  version: 2
  ethernets:
    eth0:  # WAN
      dhcp4: true
    eth1:  # LAN
      addresses:
        - 192.168.1.1/24
      dhcp4: no
```

Aplicar cambios:
```bash
sudo netplan apply
```

### Credenciales por Defecto

```
admin:admin123
user1:password1
```

## 🏗️ Arquitectura

### Diagrama de Red

```
┌─────────────────┐
│    Internet     │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Router  │
    └────┬────┘
         │ eth0 (WAN)
┌────────┴─────────────┐
│  Linux Gateway       │
│  NetGuard Portal     │
│  - 192.168.1.1       │
│  - iptables          │
│  - HTTP Server :8080 │
└────────┬─────────────┘
         │ eth1 (LAN)
    ┌────┴────┐
    │ Switch  │
    └────┬────┘
         │
    ┌────┴────────┬──────────┬────────┐
    │             │          │        │
┌───┴───┐   ┌────┴────┐ ┌───┴──┐ ┌──┴───┐
│Client1│   │Client 2 │ │Client│ │Client│
│  .100 │   │  .101   │ │ .102 │ │ .103 │
└───────┘   └─────────┘ └──────┘ └──────┘
```

### Flujo de Autenticación

```
1. Cliente → DHCP Request → Gateway
2. Gateway → IP Assignment → Cliente (192.168.1.x)
3. Cliente → HTTP Request → Any Website
4. iptables → Intercept → Redirect to :8080
5. Gateway → Login Page → Cliente
6. Cliente → POST /login (credentials) → Gateway
7. Gateway → Validate → Database
8. Gateway → Add iptables rule → Allow IP
9. Gateway → Success Response → Cliente
10. Cliente → Internet Access ✓
```

## 📚 Referencias

- [iptables Documentation](https://netfilter.org/documentation/)
- [Python http.server](https://docs.python.org/3/library/http.server.html)
- [dnsmasq Manual](http://www.thekelleys.org.uk/dnsmasq/doc.html)
- [Linux Networking](https://www.kernel.org/doc/html/latest/networking/)

## 📝 Licencia

Proyecto educativo - Uso libre para aprendizaje

## 👨‍💻 Autor

Desarrollado para el curso de Networking

---

**⚠️ ADVERTENCIA**: Este portal cautivo es para propósitos educativos. 
