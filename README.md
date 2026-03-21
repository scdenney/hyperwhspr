# hyperwhspr

Voice-to-text on Omarchy/Hyprland using [hyprwhspr](https://github.com/goodroot/hyprwhspr) — the Linux equivalent of Wispr Flow.

## Current setup

- **Version:** hyprwhspr v1.19.0
- **Model:** nemo-canary-1b-v2 (1B params, fp32, no quantization)
- **Backend:** onnx-asr (GPU)
- **Hardware:** RTX 3060 Ti, ~5.7GB VRAM in use
- **Shortcut:** SUPER+ALT+D (toggle mode)
- **Threads:** 8, VAD on, filler word filtering on, mic OSD on

## CUDA / GPU notes

System has CUDA 13, but hyprwhspr's onnx-asr requires CUDA 12. Solved by:
- Installing CUDA 12 pip packages (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, etc.) into the hyprwhspr venv
- Adding them to `LD_LIBRARY_PATH` in the systemd user service (see `config/hyprwhspr.service`)

The `LD_LIBRARY_PATH` in the service points to:
```
~/.local/share/hyprwhspr/venv/lib/python3.14/site-packages/nvidia/*/lib
```

## Files

| File | Description |
|------|-------------|
| `config/config.json` | Main hyprwhspr config (copy of `~/.config/hyprwhspr/config.json`) |
| `config/hyprwhspr.service` | Systemd user service (copy of `~/.config/systemd/user/hyprwhspr.service`) |

> Note: `config.json` has a `"model": "base.en"` field — this is a legacy whisper.cpp field and is ignored. The active model is set via `"onnx_asr_model": "nemo-canary-1b-v2"`.

## Service management

```bash
systemctl --user status hyprwhspr
systemctl --user restart hyprwhspr
systemctl --user stop hyprwhspr
journalctl --user -u hyprwhspr -f   # live logs
```

## Known issues / fixes

| Date | Issue | Fix |
|------|-------|-----|
| 2026-03-19 | Mic OSD stale daemon | `systemctl --user restart hyprwhspr` |
