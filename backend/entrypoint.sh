#!/bin/sh
# ======================================================
# AI News Studio — Container Entrypoint
# ======================================================
# Creates media directories at runtime instead of build time.
# This avoids Docker volume conflicts when the volume already
# contains a file/dir at the expected path from a prior run.
# ======================================================

set -e

# Ensure media directories exist (idempotent)
mkdir -p /app/media/generated /app/media/temp /app/media/thumbnails

# Hand off to the CMD
exec "$@"
