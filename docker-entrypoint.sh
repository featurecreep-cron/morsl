#!/bin/sh
# Morsl container entrypoint.
#
# PUID/PGID support (linuxserver.io convention):
#   If PUID or PGID are set, adjust the appuser UID/GID at startup
#   and chown data directories. Requires starting as root.
#   If not set, runs as the default appuser (UID 1000).

PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Ensure writable subdirectories exist under the mounted data volume.
# When ./data is bind-mounted from the host, the container's pre-built
# directories are replaced, so we recreate them at startup.
for dir in data/branding data/custom-icons data/profiles data/templates data/weekly_plans; do
    mkdir -p "$dir" 2>/dev/null || true
done
mkdir -p web/icons 2>/dev/null || true

# If running as root and PUID/PGID differ from defaults, adjust ownership
if [ "$(id -u)" = "0" ]; then
    if [ "$PUID" != "1000" ] || [ "$PGID" != "1000" ]; then
        groupmod -o -g "$PGID" appgroup 2>/dev/null || true
        usermod -o -u "$PUID" appuser 2>/dev/null || true
    fi
    chown -R appuser:appgroup data web/icons
    exec gosu appuser "$@"
fi

# Not root — run directly (default container behavior)
exec "$@"
