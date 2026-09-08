#!/bin/sh
# ======================================================
# AI News Studio — Container Entrypoint
# ======================================================
# Creates media directories at runtime (idempotent), fixes
# ownership on Docker-volume-mounted paths, then drops
# privileges to appuser for production.
# ======================================================

set -e

# Ensure media directories exist (works even on existing volumes)
# Remove stale files that conflict with expected directory paths
for dir in /app/media/generated /app/media/temp /app/media/thumbnails; do
    if [ -f "$dir" ]; then
        rm -f "$dir"
    fi
    mkdir -p "$dir"
done

# If running as root AND appuser exists, fix ownership and drop privileges
if [ "$(id -u)" = "0" ]; then
    # Fix volume ownership so appuser can write
    if id appuser > /dev/null 2>&1; then
        chown -R appuser:appuser /app/media
        exec gosu appuser "$@"
    fi
fi

# Development stage (already running as root, no appuser)
exec "$@"
