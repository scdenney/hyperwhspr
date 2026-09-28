#!/usr/bin/env bash
# hyprwhspr audio stack watchdog
#
# Heals the two recurring failure modes documented in
# o_system/hyperwhspr/README.md (known issues 2026-08-11 / 2026-08-12):
#
#  1. wireplumber 0.5.15 leaks GObject weak references until it hits GLib's
#     65535 GWeakRef cap ("Too many GWeakRef registered"), after which the
#     session manager can no longer route capture streams: the pulse layer
#     returns zero audio bytes and hyprwhspr's stream-open blocks forever.
#     Heal: restart the PipeWire stack at the FIRST cap message, before the
#     graph stalls. hyprwhspr detects the pulse restart and self-recovers.
#
#  2. hyprwhspr already wedged against a stalled graph ("Recording thread
#     did not exit cleanly" / "Cleanup still owns the audio stream").
#     Heal: restart the PipeWire stack AND hyprwhspr.
#
# Runs as a user service: hyprwhspr-audio-watchdog.service
set -u

COOLDOWN=600  # seconds between heals
last_heal=0

log() { echo "[watchdog] $*"; }

heal() {
    local reason="$1"
    local now
    now=$(date +%s)
    if (( now - last_heal < COOLDOWN )); then
        return
    fi
    last_heal=$now
    log "trigger: $reason - restarting PipeWire stack"
    systemctl --user restart pipewire pipewire-pulse wireplumber
    sleep 3
    if [[ "$reason" == wedge ]]; then
        log "hyprwhspr was wedged - restarting it too"
        systemctl --user restart hyprwhspr
    fi
    log "heal complete ($reason)"
}

log "watching wireplumber + hyprwhspr journals"
journalctl --user -f -n 0 -o cat -u wireplumber -u hyprwhspr | while read -r line; do
    case "$line" in
        *"Too many GWeakRef registered"*)
            heal "gweakref-cap" ;;
        *"Cleanup still owns the audio stream"*|*"Recording thread did not exit cleanly"*)
            heal "wedge" ;;
    esac
done
