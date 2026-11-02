# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

FROM httpd:2.4

# Enable built-in modules for security and rate limiting
RUN sed -i 's/#LoadModule rewrite_module/LoadModule rewrite_module/' /usr/local/apache2/conf/httpd.conf
RUN sed -i 's/#LoadModule headers_module/LoadModule headers_module/' /usr/local/apache2/conf/httpd.conf

# The site's own sign-in page and session cookie (mod_auth_form, see
# local.conf); the build fails if the image does not have a module
RUN for m in auth_form session session_cookie session_crypto request; do \
      sed -i "s|^#\(LoadModule ${m}_module \)|\1|" /usr/local/apache2/conf/httpd.conf \
      && grep -q "^LoadModule ${m}_module " /usr/local/apache2/conf/httpd.conf; \
    done

# The passphrase that encrypts the session cookie is made when the container
# starts, if there is none (signing in again is needed after a re-creation)
CMD ["sh", "-c", "[ -s /usr/local/apache2/conf/session.key ] || head -c 48 /dev/urandom | base64 > /usr/local/apache2/conf/session.key; exec httpd-foreground"]

# Note: We'll use Apache's built-in rate limiting instead of mod_evasive
# This avoids compilation complexity while still providing security

# Copiar configuración
# Local reverse proxy (also mounted by docker-compose.local.yml for quick edits)
COPY local.conf /usr/local/apache2/conf/extra/httpd-proxy.conf
COPY security.conf /usr/local/apache2/conf/extra/security.conf

# Include configurations
RUN echo "Include conf/extra/httpd-proxy.conf" >> /usr/local/apache2/conf/httpd.conf
RUN echo "Include conf/extra/security.conf" >> /usr/local/apache2/conf/httpd.conf

# Certificates are mounted at runtime (see docker-compose files and
# setup-local-certs.sh); private keys are never baked into the image.
