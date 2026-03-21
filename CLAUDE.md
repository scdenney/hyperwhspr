# hyprwhspr context for Claude

This folder tracks the hyprwhspr voice-to-text setup on this machine.

## What lives here

- `README.md` — setup overview, CUDA notes, service commands, known issues log
- `config/config.json` — snapshot of `~/.config/hyprwhspr/config.json`
- `config/hyprwhspr.service` — snapshot of `~/.config/systemd/user/hyprwhspr.service`

## Key facts

- Active config is at `~/.config/hyprwhspr/config.json`
- Service file is at `~/.config/systemd/user/hyprwhspr.service`
- GPU acceleration works via CUDA 12 pip packages in the hyprwhspr venv + `LD_LIBRARY_PATH` in the service
- When making changes to the service: `systemctl --user daemon-reload && systemctl --user restart hyprwhspr`
- When updating config snapshots here, copy from the live paths above

## When helping with hyprwhspr

- Check README.md known issues table before diagnosing recurring problems
- Update the known issues table after resolving anything new
- Keep config snapshots in sync with live files after any changes
