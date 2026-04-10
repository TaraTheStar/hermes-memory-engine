#!/bin/sh
set -e

case "${1}" in
    test)
        shift
        exec python3 -m pytest tests/ -v "$@"
        ;;
    mcp)
        exec python3 src/mcp_server.py
        ;;
    *)
        exec "$@"
        ;;
esac
