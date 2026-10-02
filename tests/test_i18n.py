# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""The translation checker (tools/check-i18n.py) passes."""
import subprocess
import sys

from conftest import ROOT


def test_translations_complete():
    run = subprocess.run([sys.executable, str(ROOT / "tools" / "check-i18n.py")], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
