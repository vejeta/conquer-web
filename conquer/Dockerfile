# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

ARG DEBIAN_TAG=stable-slim

# -----------------------------------------------------------------------------
# Build stage: compile Conquer and fetch ttyd
# -----------------------------------------------------------------------------
FROM debian:${DEBIAN_TAG} AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git build-essential libncurses-dev \
    && rm -rf /var/lib/apt/lists/*

# Conquer hardcodes its data (DEFAULTDIR) and binary (EXEDIR) paths at
# compile time. Build with a fixed prefix so help files and conqsort are found:
#   /opt/conquer/bin  -> conquer, conqrun, conqsort, conqowner
#   /opt/conquer/lib  -> live world data (mounted as a volume)
ENV CONQUER_PREFIX=/opt/conquer

# Game sources: the repository's default branch unless CONQUER_REF names a
# branch, tag or commit (recommended for reproducible builds)
ARG CONQUER_REPO=https://github.com/vejeta/conquer.git
ARG CONQUER_REF=
WORKDIR /src
RUN git clone "${CONQUER_REPO}" conquer && \
    if [ -n "${CONQUER_REF}" ]; then git -C conquer checkout "${CONQUER_REF}"; fi && \
    git -C conquer log -1 --format='Conquer sources: %H %s'

WORKDIR /src/conquer/gpl-release
RUN make PREFIX=${CONQUER_PREFIX} && \
    mkdir -p ${CONQUER_PREFIX}/bin ${CONQUER_PREFIX}/lib ${CONQUER_PREFIX}/share && \
    cp conquer conqrun conqsort ${CONQUER_PREFIX}/bin/ && \
    cp help0 help1 help2 help3 help4 help5 ${CONQUER_PREFIX}/share/

# conqowner: fixes the god nation owner so the admin can add every nation
# (built against the game headers so the data layout always matches)
COPY tools/conqowner.c /src/conqowner.c
RUN gcc -std=gnu99 -D_GNU_SOURCE -O2 -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=600 \
        -DDEFAULTDIR=\"${CONQUER_PREFIX}/lib\" -DEXEDIR=\"${CONQUER_PREFIX}/bin\" \
        -DVERSION=\"4\" -DPATCHLEVEL=\"12\" -DLOGIN=\"root\" -DADMIN -DCONQUER \
        -I. -o ${CONQUER_PREFIX}/bin/conqowner /src/conqowner.c

# ttyd: official static release binary, pinned and checksum-verified.
# The checksums belong to this version; update both together.
ARG TTYD_VERSION=1.7.7
ARG TARGETARCH
RUN arch="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    case "${arch}" in \
        amd64) asset=ttyd.x86_64;  sum=8a217c968aba172e0dbf3f34447218dc015bc4d5e59bf51db2f2cd12b7be4f55 ;; \
        arm64) asset=ttyd.aarch64; sum=b38acadd89d1d396a0f5649aa52c539edbad07f4bc7348b27b4f4b7219dd4165 ;; \
        *) echo "Unsupported architecture: ${arch}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /usr/local/bin/ttyd \
        "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/${asset}" && \
    echo "${sum}  /usr/local/bin/ttyd" | sha256sum -c - && \
    chmod 755 /usr/local/bin/ttyd

# -----------------------------------------------------------------------------
# Runtime stage: only what the game, the menu and the turn scheduler need
# -----------------------------------------------------------------------------
FROM debian:${DEBIAN_TAG}

# - libncurses6: the game's terminal UI
# - cron/tzdata: scheduled turn updates in the configured time zone
# - curl: container health check
# - less: pager for scores in the player menu
RUN apt-get update && apt-get install -y --no-install-recommends \
    libncurses6 cron tzdata curl less \
    && rm -rf /var/lib/apt/lists/*

ENV CONQUER_PREFIX=/opt/conquer
ENV PATH="${CONQUER_PREFIX}/bin:${PATH}"

COPY --from=build /usr/local/bin/ttyd /usr/local/bin/ttyd
COPY --from=build ${CONQUER_PREFIX} ${CONQUER_PREFIX}

# Default world shipped with the image. It is copied into the data volume
# on first start only, so player progress survives rebuilds.
COPY lib/ ${CONQUER_PREFIX}/default-world/

# Container scripts
COPY scripts/entrypoint.sh /usr/local/bin/conquer-entrypoint
COPY scripts/menu.sh /usr/local/bin/conquer-menu
COPY scripts/turn.sh /usr/local/bin/conquer-turn
COPY scripts/status.sh /usr/local/bin/conquer-status
RUN chmod 755 /usr/local/bin/conquer-entrypoint /usr/local/bin/conquer-menu \
    /usr/local/bin/conquer-turn /usr/local/bin/conquer-status

VOLUME ["/opt/conquer/lib", "/opt/conquer/public"]

# ttyd listens here; Apache proxies /play/ to it
EXPOSE 7681

# ttyd answers 401 without credentials, so authenticate the probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS -o /dev/null -u "${TTYD_USERNAME:-conquer}:${TTYD_PASSWORD:-changeme}" http://localhost:7681/play/ || exit 1

CMD ["/usr/local/bin/conquer-entrypoint"]
