#!/bin/bash
DOMAIN="conquer.vejeta.com"
CERTS_DIR="$(pwd)/apache/certs"

# Asegúrate de que el directorio existe
mkdir -p "$CERTS_DIR"

# Ejecuta certbot en modo webroot, usando la ruta expuesta en Apache
docker run --rm -it \
  -v "$CERTS_DIR:/etc/letsencrypt" \
  -v "$CERTS_DIR:/var/lib/letsencrypt" \
  certbot/certbot certonly \
  --webroot \
  --webroot-path=/var/lib/letsencrypt \
  -d "$DOMAIN" \
  --agree-tos \
  --no-eff-email \
  -m admin@"$DOMAIN"

# Recargar Apache dentro del contenedor (sin reiniciar todo)
docker exec apache apachectl graceful
