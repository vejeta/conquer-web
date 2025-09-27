#!/bin/bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

# Wrapper script for certificate renewal that can be called from anywhere
cd "$(dirname "$0")"
exec ./apache/renew-certs.sh "$@"