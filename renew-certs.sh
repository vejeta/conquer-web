#!/bin/bash
# Wrapper script for certificate renewal that can be called from anywhere
cd "$(dirname "$0")"
exec ./apache/renew-certs.sh "$@"