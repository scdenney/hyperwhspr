# hyperwhspr

Voice-to-text on Omarchy/Hyprland using [hyprwhspr](https://github.com/goodroot/hyprwhspr) — the Linux equivalent of Wispr Flow.

## Current setup

- **Version:** hyprwhspr v1.19.0
- **Backend:** OpenAI REST API — GPT-4o Transcribe
- **Shortcut:** SUPER+ALT+D (toggle mode)
- **Threads:** 8, filler word filtering on, mic OSD on
- **API key:** stored in `~/.local/share/hyprwhspr/credentials` (not in git)

## Files

| File | Description |
|------|-------------|
| `config/config.json` | Main hyprwhspr config (copy of `~/.config/hyprwhspr/config.json`) |
| `config/hyprwhspr.service` | Systemd user service (copy of `~/.config/systemd/user/hyprwhspr.service`) |

## Service management

```bash
systemctl --user status hyprwhspr
systemctl --user restart hyprwhspr
systemctl --user stop hyprwhspr
journalctl --user -u hyprwhspr -f   # live logs
```

## Switching backends

### Current: OpenAI GPT-4o Transcribe (cloud)

```json
{
  "transcription_backend": "rest-api",
  "rest_endpoint_url": "https://api.openai.com/v1/audio/transcriptions",
  "rest_api_provider": "openai",
  "rest_api_key": null,
  "rest_headers": {},
  "rest_body": {"model": "gpt-4o-transcribe"}
}
```

API key stored via: `~/.local/share/hyprwhspr/credentials`

### Previous: Local onnx-asr (GPU, nemo-canary-1b-v2)

~5.7GB VRAM, no internet required, instant response, no cost.

```json
{
  "transcription_backend": "onnx-asr",
  "rest_endpoint_url": null,
  "rest_api_provider": null,
  "rest_api_key": null,
  "rest_headers": {},
  "rest_body": {},
  "onnx_asr_model": "nemo-canary-1b-v2",
  "onnx_asr_quantization": null,
  "onnx_asr_use_vad": true
}
```

Requires `LD_LIBRARY_PATH` in service pointing to CUDA 12 pip packages in venv (system has CUDA 13 — see `config/hyprwhspr.service`).

After any config change: `systemctl --user restart hyprwhspr`

## Known issues / fixes

| Date | Issue | Fix |
|------|-------|-----|
| 2026-03-19 | Mic OSD stale daemon | `systemctl --user restart hyprwhspr` |
| 2026-03-21 | Switched to GPT-4o Transcribe | Working as of switch |
