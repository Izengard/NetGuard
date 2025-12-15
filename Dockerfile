FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema necesarias para iptables/dnsmasq en pruebas dentro del contenedor
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       iproute2 iptables dnsmasq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar proyecto
COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["bash"]
