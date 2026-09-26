# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

FROM httpd:2.4

# Enable built-in modules for security and rate limiting
RUN sed -i 's/#LoadModule rewrite_module/LoadModule rewrite_module/' /usr/local/apache2/conf/httpd.conf
RUN sed -i 's/#LoadModule headers_module/LoadModule headers_module/' /usr/local/apache2/conf/httpd.conf

# Note: We'll use Apache's built-in rate limiting instead of mod_evasive
# This avoids compilation complexity while still providing security

# Copiar configuración
COPY extra.conf /usr/local/apache2/conf/extra/httpd-proxy.conf
COPY security.conf /usr/local/apache2/conf/extra/security.conf

# Include configurations
RUN echo "Include conf/extra/httpd-proxy.conf" >> /usr/local/apache2/conf/httpd.conf
RUN echo "Include conf/extra/security.conf" >> /usr/local/apache2/conf/httpd.conf

# Certificates are mounted at runtime (see docker-compose files and
# setup-local-certs.sh); private keys are never baked into the image.
