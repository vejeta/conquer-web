# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

FROM debian:stable-slim

# Security build arguments (OVERRIDE THESE IN PRODUCTION!)
ARG TTYD_USERNAME=conquer
ARG TTYD_PASSWORD=changeme
ARG MAX_CLIENTS=5
ARG SESSION_TIMEOUT=1800

# Build and runtime dependencies
# - cron/tzdata: scheduled turn updates in the configured time zone
# - curl: container health check
# - less: pager for scores in the player menu
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git build-essential libncurses5-dev libncursesw5-dev \
    cmake libjson-c-dev libwebsockets-dev \
    cron tzdata curl less \
    && rm -rf /var/lib/apt/lists/*

# Clone and compile ttyd
WORKDIR /opt
RUN git clone https://github.com/tsl0922/ttyd.git
RUN mkdir -p /opt/ttyd/build
WORKDIR /opt/ttyd/build
RUN cmake .. && make && make install

# Conquer hardcodes its data (DEFAULTDIR) and binary (EXEDIR) paths at
# compile time. Build with a fixed prefix so help files and conqsort are found:
#   /opt/conquer/bin  -> conquer, conqrun, conqsort
#   /opt/conquer/lib  -> live world data (mounted as a volume)
ENV CONQUER_PREFIX=/opt/conquer
WORKDIR /root
RUN git clone https://github.com/vejeta/conquer.git
WORKDIR /root/conquer/gpl-release
RUN make PREFIX=${CONQUER_PREFIX} && \
    mkdir -p ${CONQUER_PREFIX}/bin ${CONQUER_PREFIX}/lib ${CONQUER_PREFIX}/share && \
    cp conquer conqrun conqsort ${CONQUER_PREFIX}/bin/ && \
    cp help0 help1 help2 help3 help4 help5 ${CONQUER_PREFIX}/share/

# conqowner: fixes the god nation owner so the admin can add every nation
# (built against the game headers so the data layout always matches)
COPY tools/conqowner.c /root/conqowner.c
RUN gcc -std=gnu99 -D_GNU_SOURCE -O2 -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=600 \
        -DDEFAULTDIR=\"${CONQUER_PREFIX}/lib\" -DEXEDIR=\"${CONQUER_PREFIX}/bin\" \
        -DVERSION=\"4\" -DPATCHLEVEL=\"12\" -DLOGIN=\"root\" -DADMIN -DCONQUER \
        -I. -o ${CONQUER_PREFIX}/bin/conqowner /root/conqowner.c

ENV PATH="${CONQUER_PREFIX}/bin:${PATH}"

# Default world shipped with the image. It is copied into the data volume
# on first start only, so player progress survives rebuilds.
COPY lib/ ${CONQUER_PREFIX}/default-world/

# Create non-root user for security
RUN useradd -m -s /bin/bash conqueruser && \
    mkdir -p /home/conqueruser && \
    chown -R conqueruser:conqueruser /home/conqueruser

# Container scripts
COPY scripts/entrypoint.sh /usr/local/bin/conquer-entrypoint
COPY scripts/menu.sh /usr/local/bin/conquer-menu
COPY scripts/turn.sh /usr/local/bin/conquer-turn
RUN chmod 755 /usr/local/bin/conquer-entrypoint /usr/local/bin/conquer-menu /usr/local/bin/conquer-turn

VOLUME ["/opt/conquer/lib"]

# Exponer el puerto de ttyd
EXPOSE 7681

# ttyd answers 401 without credentials, so authenticate the probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS -o /dev/null -u "${TTYD_USERNAME:-conquer}:${TTYD_PASSWORD:-changeme}" http://localhost:7681/play/ || exit 1

CMD ["/usr/local/bin/conquer-entrypoint"]
