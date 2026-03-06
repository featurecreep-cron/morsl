#!/bin/sh
# Ensure writable subdirectories exist under the mounted data volume.
# When ./data is bind-mounted from the host, the container's pre-built
# directories are replaced, so we recreate them at startup.
for dir in data/branding data/custom-icons data/profiles data/templates data/weekly_plans; do
    mkdir -p "$dir" 2>/dev/null || true
done
mkdir -p web/icons 2>/dev/null || true

exec "$@"
