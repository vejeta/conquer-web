#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build web/hero/map.json, the world map behind the landing page.

The map is the real default world (conquer/lib/data), turned half a turn
(180 degrees) so the landing page does not show players where the nations
of the game they are about to join are. The staged war on it (armies,
battle, conquered sectors) is given below in the world's own coordinates.

Usage:
  tools/hero/build-map.py CONQUER_SOURCES [WORLD_DIR]

CONQUER_SOURCES is a checkout of https://github.com/vejeta/conquer built
with make (its gpl-release/ has header.h and data.h); WORLD_DIR defaults to
conquer/lib. Needs gcc.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")

# The staged war, in world coordinates: Sahara (capital 81,30) and Woooo
# (75,34) march on the forts north of Darboth's capital (83,41)
WAR = {
    "armies": [
        {"mark": "S", "from": [79, 33], "to": [79, 38]},
        {"mark": "W", "from": [76, 35], "to": [79, 39]},
        {"mark": "D", "from": [82, 40], "to": [81, 39], "defender": True},
    ],
    "battle": [80, 39],
    "winner": "S",
    "conquered": [[80, 39], [81, 39], [78, 38], [79, 38], [82, 40], [83, 40], [84, 40]],
}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = os.path.join(sys.argv[1], "gpl-release")
    world = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "conquer", "lib")
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, "conqmap")
        subprocess.run(
            ["gcc", "-std=gnu99", "-D_GNU_SOURCE", "-O2", "-D_DEFAULT_SOURCE", "-D_XOPEN_SOURCE=600",
             '-DDEFAULTDIR="/nonexistent"', '-DEXEDIR="/nonexistent"', '-DVERSION="4"',
             '-DPATCHLEVEL="12"', '-DLOGIN="conquer"', "-DADMIN", "-DCONQUER", "-w",
             "-I", src, "-o", exe, os.path.join(HERE, "conqmap.c")], check=True)
        raw = json.loads(subprocess.run([exe, os.path.join(world, "data")], check=True,
                                         capture_output=True, text=True).stdout)
    w, h = raw["w"], raw["h"]

    def turn(p):
        return [w - 1 - p[0], h - 1 - p[1]]

    # Half a turn: the last row first, each row from its end
    rows = []
    for row in reversed(raw["rows"]):
        cells = [row[i:i + 4] for i in range(0, len(row), 4)]
        rows.append("".join(reversed(cells)))
    war = {
        "armies": [dict(a, **{"from": turn(a["from"]), "to": turn(a["to"])}) for a in WAR["armies"]],
        "battle": turn(WAR["battle"]),
        "winner": WAR["winner"],
        "conquered": [turn(p) for p in WAR["conquered"]],
    }
    out = {
        "w": w, "h": h,
        "nations": {str(n["id"]): n["mark"] for n in raw["nations"] if n["name"] and n["id"] > 0},
        "rows": rows,
        "war": war,
    }
    path = os.path.join(ROOT, "web", "hero", "map.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    print("wrote web/hero/map.json (%dx%d)" % (w, h))


if __name__ == "__main__":
    main()
