#!/usr/bin/env bash
# dev-reset.sh — Back up, reset, and restore config for testing the setup wizard.
# Usage: ./dev-reset.sh backup | reset | restore | factory-reset

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$ROOT/.claude/backups"
BACKUP_FILE="$BACKUP_DIR/config-backup.tar.gz"

# Paths relative to $ROOT that get backed up (files and dirs).
# Globs are expanded at backup time; missing paths are silently skipped.
BACKUP_PATHS=(
    .env
    data/settings.json
    data/categories.json
    data/generation_history.json
    data/schedules.json
    data/current_menu.json
    data/custom-icons
    data/templates
    data/weekly_plans
    data/profiles
    data/branding
)

# ── helpers ──────────────────────────────────────────────────────────────

die()  { echo "ERROR: $*" >&2; exit 1; }
info() { echo "» $*"; }

# Build a list of paths that actually exist on disk.
existing_paths() {
    local paths=()
    for p in "${BACKUP_PATHS[@]}"; do
        [[ -e "$ROOT/$p" ]] && paths+=("$p")
    done
    printf '%s\n' "${paths[@]}"
}

# ── backup ───────────────────────────────────────────────────────────────

do_backup() {
    mkdir -p "$BACKUP_DIR"

    local paths
    mapfile -t paths < <(existing_paths)

    if [[ ${#paths[@]} -eq 0 ]]; then
        die "Nothing to back up — no config files found."
    fi

    info "Backing up ${#paths[@]} path(s) → $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" -C "$ROOT" "${paths[@]}"
    info "Backup complete ($(du -h "$BACKUP_FILE" | cut -f1))."
}

# ── reset ────────────────────────────────────────────────────────────────

do_reset() {
    echo "This will wipe all settings, profiles, and cached data."
    read -rp "Are you sure? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        info "Aborted."
        exit 0
    fi

    info "Running backup first (safety net)…"
    do_backup
    echo

    # Disable .env so credentials aren't loaded.
    if [[ -f "$ROOT/.env" ]]; then
        mv "$ROOT/.env" "$ROOT/.env.bak"
        info "Renamed .env → .env.bak"
    fi

    # Remove files that trigger the "configured" state + cached menus.
    local remove=(
        data/settings.json
        data/categories.json
        data/current_menu.json
        data/generation_history.json
        data/schedules.json
    )
    for f in "${remove[@]}"; do
        if [[ -f "$ROOT/$f" ]]; then
            rm "$ROOT/$f"
            info "Removed $f"
        fi
    done

    # Remove all profile JSON files.
    local count=0
    for f in "$ROOT"/data/profiles/*.json; do
        [[ -f "$f" ]] || continue
        rm "$f"
        count=$((count + 1))
    done
    [[ $count -gt 0 ]] && info "Removed $count profile(s) from data/profiles/"

    # Restart server to clear in-memory state.
    if [[ -x "$ROOT/morsl.sh" ]]; then
        info "Restarting server (clean)…"
        "$ROOT/morsl.sh" restart-clean
    fi

    echo
    info "Reset complete. Visit http://localhost:8321/admin to test the setup wizard."
}

# ── restore ──────────────────────────────────────────────────────────────

do_restore() {
    [[ -f "$BACKUP_FILE" ]] || die "No backup found at $BACKUP_FILE"

    info "Restoring from $BACKUP_FILE…"
    tar -xzf "$BACKUP_FILE" -C "$ROOT"
    info "Files extracted."

    # Restore .env from .bak if the backup didn't contain one and .bak exists.
    if [[ ! -f "$ROOT/.env" && -f "$ROOT/.env.bak" ]]; then
        mv "$ROOT/.env.bak" "$ROOT/.env"
        info "Restored .env from .env.bak"
    elif [[ -f "$ROOT/.env.bak" ]]; then
        # Backup already restored .env; clean up the .bak.
        rm "$ROOT/.env.bak"
        info "Cleaned up .env.bak"
    fi

    # Restart server to pick up restored config.
    if [[ -x "$ROOT/morsl.sh" ]]; then
        info "Restarting server (clean)…"
        "$ROOT/morsl.sh" restart-clean
    fi

    echo
    info "Restore complete. Everything should be back to normal."
}

# ── main ─────────────────────────────────────────────────────────────────

case "${1:-}" in
    backup)          do_backup  ;;
    reset|factory-reset) do_reset   ;;
    restore)         do_restore ;;
    *)
        echo "Usage: $0 {backup|reset|restore|factory-reset}"
        echo
        echo "  backup        — Archive config to .claude/backups/config-backup.tar.gz"
        echo "  reset         — Back up, then wipe config for a fresh-install experience"
        echo "  factory-reset — Alias for reset"
        echo "  restore       — Restore config from the last backup"
        exit 1
        ;;
esac
