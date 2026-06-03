# hyperwhspr local voice setup

This repository documents a local voice-to-text setup for Linux/Hyprland using
[hyprwhspr](https://github.com/goodroot/hyprwhspr). It is not an application or
package. It is a reproducible configuration pattern: keyboard-triggered voice
recording, transcription, post-transcription LLM cleanup, and a calibration
loop for improving vocabulary, style, and written prosody over time.

> **macOS counterpart:** [`scdenney/macwhspr`](https://github.com/scdenney/macwhspr)
> ports this pipeline to Mac. Same `cleanup.py` prompt and `vocab.md` format,
> same `/hypr-calibrate` loop; Karabiner-Elements + Hammerspoon + a Python
> launchd daemon replace the Linux pieces. Triggered by the Globe/Fn key.

The current version of this setup uses the OpenAI API for both transcription and
cleanup:

- hyprwhspr records audio from the microphone.
- OpenAI `gpt-4o-transcribe` converts speech to text through
  `/v1/audio/transcriptions`.
- A post-transcription hook sends the raw transcript to an LLM cleanup prompt.
- The hook logs raw and cleaned text pairs so the setup can be calibrated later.
- A Claude Code command, `/hypr-calibrate`, reviews those logs and updates the
  vocabulary/style file.

The same structure can be run more locally. hyprwhspr supports an `onnx-asr`
backend, and the cleanup hook can point at a local OpenAI-compatible chat
completion server instead of OpenAI. To keep the whole pipeline private, both
the transcription backend and the cleanup LLM need to be local.

## Why use this setup

- **Fast dictation in any text field:** toggle recording, speak, and paste the
  cleaned result.
- **Local control:** the service, prompt, vocabulary, and cleanup behavior are
  plain files in `~/.config/hyprwhspr`.
- **Style calibration:** repeated transcription errors and preferred phrasing can
  be captured in `vocab.md`.
- **Backend flexibility:** use OpenAI for quality and low setup cost, or local
  models for privacy and no per-use API cost.

## Trade-offs

| Setup | Positives | Trade-offs |
| --- | --- | --- |
| OpenAI transcription + OpenAI cleanup | Strong transcription quality, simple setup, no local GPU requirement, generally fast enough for daily dictation | Sends audio/text to an API, has usage cost, depends on network/API availability |
| Local transcription + OpenAI cleanup | Keeps raw audio local, reduces API use, keeps high-quality cleanup | Cleaned transcript still leaves the machine, local ASR needs compatible hardware and model setup |
| Local transcription + local cleanup LLM | Best privacy, no API cost, full local control | More setup, more maintenance, higher hardware requirements, possible latency/speed trade-offs, local models may need prompt tuning |

## Repository contents

| File | Purpose |
| --- | --- |
| `config/config.json` | Example hyprwhspr config using OpenAI transcription |
| `config/cleanup.py` | Post-transcription cleanup hook |
| `config/vocab.md` | Vocabulary, style, and written-prosody preferences |
| `config/hyprwhspr.service` | Example systemd user service |
| `claude/commands/hypr-calibrate.md` | Claude Code command for reviewing cleanup logs and updating `vocab.md` |

## Install outline

Install hyprwhspr first by following the upstream project instructions. Then
copy the files from this repository into the expected local locations:

```bash
mkdir -p ~/.config/hyprwhspr ~/.config/systemd/user ~/.claude/commands

cp config/config.json ~/.config/hyprwhspr/config.json
cp config/cleanup.py ~/.config/hyprwhspr/cleanup.py
cp config/vocab.md ~/.config/hyprwhspr/vocab.md
cp config/hyprwhspr.service ~/.config/systemd/user/hyprwhspr.service
cp claude/commands/hypr-calibrate.md ~/.claude/commands/hypr-calibrate.md

chmod +x ~/.config/hyprwhspr/cleanup.py
```

Edit `~/.config/hyprwhspr/config.json` and replace:

```json
"post_transcription_hook": "/home/YOUR_USER/.config/hyprwhspr/cleanup.py"
```

with your real home directory path.

Also edit the first line of `~/.config/hyprwhspr/cleanup.py` so it points to the
Python interpreter used by hyprwhspr:

```python
#!/home/YOUR_USER/.local/share/hyprwhspr/venv/bin/python
```

Reload and start the service:

```bash
systemctl --user daemon-reload
systemctl --user enable --now hyprwhspr
systemctl --user status hyprwhspr
```

Useful service commands:

```bash
systemctl --user restart hyprwhspr
systemctl --user stop hyprwhspr
journalctl --user -u hyprwhspr -f
```

## OpenAI API setup

The example config uses OpenAI's speech-to-text endpoint with
`gpt-4o-transcribe`. OpenAI's audio docs describe the transcription endpoint and
the supported transcription models:
<https://platform.openai.com/docs/guides/speech-to-text>.

Store your API key outside git:

```bash
mkdir -p ~/.local/share/hyprwhspr
chmod 700 ~/.local/share/hyprwhspr
printf '{"openai":"YOUR_OPENAI_API_KEY"}\n' > ~/.local/share/hyprwhspr/credentials
chmod 600 ~/.local/share/hyprwhspr/credentials
```

The relevant hyprwhspr config block is:

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

The cleanup hook defaults to `gpt-4.1-mini` through the OpenAI Chat Completions
API. Install its Python dependency in the environment used by hyprwhspr:

```bash
~/.local/share/hyprwhspr/venv/bin/pip install httpx
```

You can override the cleanup model or endpoint with environment variables in the
service file:

```ini
Environment=HYPRWHSPR_CLEANUP_MODEL=gpt-4.1-mini
Environment=HYPRWHSPR_LLM_API_URL=https://api.openai.com/v1/chat/completions
```

## Local transcription option

hyprwhspr can use local ONNX ASR instead of the REST API. The previous local
configuration for this setup used `nemo-canary-1b-v2` with VAD enabled:

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

On the tested machine this used roughly 5.7 GB of VRAM. A local model removes
transcription API cost and keeps audio on the machine, but the actual speed
depends heavily on model size, GPU/CPU, drivers, and quantization. It may be
faster than an API when the model is warm and the GPU is suitable; it may be
slower or less accurate on weaker hardware.

If CUDA libraries from the hyprwhspr virtual environment are needed, adapt the
`LD_LIBRARY_PATH` example in `config/hyprwhspr.service` to match your Python and
CUDA package versions.

## Local cleanup LLM option

The cleanup hook can call any local server that exposes an OpenAI-compatible
`/v1/chat/completions` endpoint. For example, if a local LLM server is listening
on port 11434:

```ini
Environment=HYPRWHSPR_LLM_API_URL=http://127.0.0.1:11434/v1/chat/completions
Environment=HYPRWHSPR_CLEANUP_MODEL=llama3.1:8b
```

For full privacy, combine this with local ONNX ASR. If only the cleanup model is
local while transcription still uses OpenAI, audio still leaves the machine. If
only transcription is local while cleanup still uses OpenAI, the transcript text
still leaves the machine.

## Cleanup prompt

`config/cleanup.py` is deliberately constrained. It tells the model to behave as
a text reformatter, not as an assistant. It should not answer questions,
summarize the dictated content, or acknowledge instructions. It should only
return the cleaned-up transcript.

The prompt currently asks the model to fix:

- punctuation
- capitalization
- grammar
- filler words
- false starts
- speech disfluencies
- paragraph breaks
- list formatting when the content clearly calls for it
- professional register

Change the global behavior in `SYSTEM_PROMPT` inside `config/cleanup.py`.
Change recurring vocabulary, formatting, and written-prosody preferences in
`config/vocab.md`.

## Calibration loop

Every cleanup is logged to:

```text
~/.config/hyprwhspr/cleanup_log.jsonl
```

The log contains raw and cleaned pairs. In Claude Code, run:

```text
/hypr-calibrate
```

The command reviews recent log entries, identifies repeated vocabulary and style
patterns, and proposes edits to:

```text
~/.config/hyprwhspr/vocab.md
```

This is the main way to tune "prosody" in the practical written sense: sentence
rhythm, punctuation habits, preferred register, spelling of proper nouns, and
the amount of cleanup the model should apply.

## Known issues and fixes

| Date | Issue | Fix |
| --- | --- | --- |
| 2026-03-19 | Mic OSD stale daemon | `systemctl --user restart hyprwhspr` |
| 2026-03-21 | Switched to GPT-4o Transcribe | Working as of switch |
| 2026-05-13 | Omarchy update broke mic OSD and `wl-copy` because `WAYLAND_DISPLAY` was not inherited by the service | Added `PassEnvironment=WAYLAND_DISPLAY DISPLAY` and an `ExecStartPre` guard that waits for UWSM to export `WAYLAND_DISPLAY` into the systemd user environment |

## Security notes

- Do not commit `~/.local/share/hyprwhspr/credentials`.
- Do not commit `~/.config/hyprwhspr/cleanup_log.jsonl`; it may contain private
  dictated text.
- Review `vocab.md` before publishing if it includes personal names, project
  names, or sensitive vocabulary.
