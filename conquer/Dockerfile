# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

FROM debian:stable-slim

# Security build arguments (OVERRIDE THESE IN PRODUCTION!)
ARG TTYD_USERNAME=conquer
ARG TTYD_PASSWORD=changeme
ARG MAX_CLIENTS=5
ARG SESSION_TIMEOUT=1800

# Dependencias
RUN apt-get update && apt-get install -y \
    git build-essential libncurses5-dev libncursesw5-dev \
    cmake libjson-c-dev libwebsockets-dev

# Clone and compile ttyd
WORKDIR /opt
RUN git clone https://github.com/tsl0922/ttyd.git
RUN mkdir -p /opt/ttyd/build
WORKDIR /opt/ttyd/build
RUN cmake .. && make && make install

# Clonar y compilar Conquer
WORKDIR /root
RUN git clone https://github.com/vejeta/conquer.git
WORKDIR /root/conquer/gpl-release
RUN make
#RUN make install

# This will copy an externally generated world data into the docker image.
COPY lib/ ./lib/
COPY lib/.userlog ./lib/.userlog

# Create non-root user for security
RUN useradd -m -s /bin/bash conqueruser && \
    mkdir -p /home/conqueruser && \
    chown -R conqueruser:conqueruser /home/conqueruser

# Create symlink for game data directory (game expects /usr/lib/conquer)
RUN mkdir -p /usr/lib && ln -sf /root/conquer/gpl-release/lib /usr/lib/conquer

# Create a startup script with security
RUN echo '#!/bin/bash' > /start-conquer.sh && \
    echo 'cd /root/conquer/gpl-release' >> /start-conquer.sh && \
    echo 'export TERM=xterm-256color' >> /start-conquer.sh && \
    echo 'echo "=== CONQUER GAME ==="' >> /start-conquer.sh && \
    echo 'echo "Authenticated user session"' >> /start-conquer.sh && \
    echo 'echo "Waiting for terminal to be ready..."' >> /start-conquer.sh && \
    echo 'sleep 2' >> /start-conquer.sh && \
    echo 'echo "Starting game now..."' >> /start-conquer.sh && \
    echo 'exec ./conquer' >> /start-conquer.sh && \
    chmod +x /start-conquer.sh

# Exponer el puerto de ttyd
EXPOSE 7681

# Lanzar conquer con ttyd usando el script

# Create final startup script with environment variable substitution
RUN echo '#!/bin/bash' > /start-ttyd.sh && \
    echo 'exec ttyd -p 7681 -W -m ${MAX_CLIENTS:-5} -c ${TTYD_USERNAME:-conquer}:${TTYD_PASSWORD:-changeme} -P ${SESSION_TIMEOUT:-1800} -t titleFixed=Conquer -t fontSize=16 -t disableLeaveAlert=true /start-conquer.sh' >> /start-ttyd.sh && \
    chmod +x /start-ttyd.sh

CMD ["/start-ttyd.sh"]
