FROM httpd:2.4

# Copiar configuración
COPY extra.conf /usr/local/apache2/conf/extra/httpd-proxy.conf

# ⭐ ADD THIS LINE ⭐
RUN echo "Include conf/extra/httpd-proxy.conf" >> /usr/local/apache2/conf/httpd.conf

# Incluir certificado self-signed por defecto
COPY certs/selfsigned/ /usr/local/apache2/conf/certs/live/conquer.local/
