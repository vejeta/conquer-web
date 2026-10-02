# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The compose files work with docker-compose 1.29 too (Debian's): it hands
${VARIABLES} to Docker as strings, which Docker refuses for numeric
settings such as pids_limit."""
import re

import pytest

from conftest import ROOT

NUMERIC = ("pids_limit", "cpus", "cpu_shares", "shm_size", "mem_limit", "memswap_limit", "oom_score_adj")


@pytest.mark.parametrize("name", ["docker-compose.vps.yml", "docker-compose.local.yml"])
def test_numeric_settings_are_literal(name):
    for n, line in enumerate((ROOT / name).read_text().splitlines(), 1):
        m = re.match(r"\s*(\w+):\s*(.*)", line)
        if m and m.group(1) in NUMERIC:
            assert "${" not in m.group(2), "%s:%d: %s cannot be a variable for docker-compose 1.29" % (name, n, m.group(1))
