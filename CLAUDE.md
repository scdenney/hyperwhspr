# hyprwhspr context for Claude

This folder tracks the hyprwhspr voice-to-text setup on this machine.

## What lives here

- `README.md` - public setup overview, OpenAI/local backend notes, service commands, known issues log
- `config/config.json` - reusable example based on `~/.config/hyprwhspr/config.json`
- `config/cleanup.py` - post-transcription LLM cleanup hook
- `config/vocab.md` - vocabulary, style, and written-prosody preferences
- `config/hyprwhspr.service` - reusable example based on `~/.config/systemd/user/hyprwhspr.service`
- `claude/commands/hypr-calibrate.md` - command for reviewing cleanup logs and updating vocab/style preferences

## Key facts

- Active config is at `~/.config/hyprwhspr/config.json`
- Service file is at `~/.config/systemd/user/hyprwhspr.service`
- GPU acceleration works via CUDA 12 pip packages in the hyprwhspr venv + `LD_LIBRARY_PATH` in the service
- Public examples should use placeholders such as `/home/YOUR_USER`, not machine-specific paths
- When making changes to the service: `systemctl --user daemon-reload && systemctl --user restart hyprwhspr`
- When updating config snapshots here, copy from the live paths above

## When helping with hyprwhspr

- Check README.md known issues table before diagnosing recurring problems
- Update the known issues table after resolving anything new
- Keep config snapshots in sync with live files after any changes
