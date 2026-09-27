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

# The game runs as this unprivileged user. Conquer compiles the building user
# (whoami) in as its administrator (LOGIN), so build as that user too: then
# turn updates and nation creation work without root.
ARG CONQUER_UID=1000
RUN useradd -m -u "${CONQUER_UID}" -s /bin/bash conquer

# Game sources: the repository's default branch unless CONQUER_REF names a
# branch, tag or commit (recommended for reproducible builds)
ARG CONQUER_REPO=https://github.com/vejeta/conquer.git
ARG CONQUER_REF=
WORKDIR /src

# Engine fixes not yet in the game repository (patches/README.md). A patch
# that is already upstream is skipped; one that no longer applies fails the
# build, so it is noticed and refreshed.
COPY patches/ /src/patches/
RUN git clone "${CONQUER_REPO}" conquer && \
    if [ -n "${CONQUER_REF}" ]; then git -C conquer checkout "${CONQUER_REF}"; fi && \
    git -C conquer log -1 --format='Conquer sources: %H %s' && \
    for p in /src/patches/*.patch; do \
        [ -e "$p" ] || continue; \
        if git -C conquer apply --whitespace=nowarn --check "$p" 2>/dev/null; then \
            git -C conquer apply --whitespace=nowarn "$p" && echo "Applied $(basename "$p")"; \
        elif git -C conquer apply --whitespace=nowarn -R --check "$p" 2>/dev/null; then \
            echo "Already in the sources: $(basename "$p")"; \
        else \
            echo "Patch does not apply: $(basename "$p")" >&2; exit 1; \
        fi; \
    done && \
    chown -R conquer:conquer conquer

WORKDIR /src/conquer/gpl-release
USER conquer
RUN make PREFIX=${CONQUER_PREFIX}
USER root
RUN mkdir -p ${CONQUER_PREFIX}/bin ${CONQUER_PREFIX}/lib ${CONQUER_PREFIX}/share && \
    cp conquer conqrun conqsort ${CONQUER_PREFIX}/bin/ && \
    cp help0 help1 help2 help3 help4 help5 ${CONQUER_PREFIX}/share/

# conqowner: fixes the god nation owner so the admin can add every nation
# (built against the game headers so the data layout always matches)
COPY tools/conqowner.c /src/conqowner.c
RUN gcc -std=gnu99 -D_GNU_SOURCE -O2 -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=600 \
        -DDEFAULTDIR=\"${CONQUER_PREFIX}/lib\" -DEXEDIR=\"${CONQUER_PREFIX}/bin\" \
        -DVERSION=\"4\" -DPATCHLEVEL=\"12\" -DLOGIN=\"conquer\" -DADMIN -DCONQUER \
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

# Same user and uid as in the build stage (the game checks it at runtime).
# The entrypoint starts as root only to prepare the volumes and cron, then
# runs ttyd, the menu, the game and every turn update as this user.
ARG CONQUER_UID=1000
RUN useradd -m -u "${CONQUER_UID}" -s /bin/bash conquer

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
COPY scripts/next-turn.sh /usr/local/bin/conquer-next-turn
COPY scripts/ready.sh /usr/local/bin/conquer-ready
RUN chmod 755 /usr/local/bin/conquer-entrypoint /usr/local/bin/conquer-menu \
    /usr/local/bin/conquer-turn /usr/local/bin/conquer-status /usr/local/bin/conquer-next-turn \
    /usr/local/bin/conquer-ready

VOLUME ["/opt/conquer/lib", "/opt/conquer/public", "/opt/conquer/backups"]

# ttyd listens here; Apache proxies /play/ to it
EXPOSE 7681

# ttyd trusts the proxy's identity header and answers 407 without it
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS -o /dev/null -H "X-WEBAUTH-USER: healthcheck" http://localhost:7681/play/ || exit 1

CMD ["/usr/local/bin/conquer-entrypoint"]
