# hyperwhspr

[![platform](https://img.shields.io/badge/platform-Linux%20%2F%20Hyprland-FCC624?logo=linux&logoColor=black)](https://hypr.land)
[![upstream](https://img.shields.io/badge/upstream-hyprwhspr-8A2BE2)](https://github.com/goodroot/hyprwhspr)
[![transcription](https://img.shields.io/badge/transcription-gpt--realtime--whisper-111111?logo=openai&logoColor=white)](https://platform.openai.com/docs/guides/speech-to-text)
[![updated](https://img.shields.io/badge/updated-July%202026-green)](https://github.com/scdenney/hyperwhspr/commits/master)
[![macOS counterpart](https://img.shields.io/badge/macOS%20counterpart-macwhspr-lightgrey?logo=apple)](https://github.com/scdenney/macwhspr)

Dictation-first voice-to-text for Linux/Hyprland, built on
[hyprwhspr](https://github.com/goodroot/hyprwhspr). This repository is not an
application or package. It is a reproducible configuration pattern:
hotkey-triggered recording, streaming transcription, post-transcription LLM
cleanup, and a calibration loop that improves vocabulary, style, and written
prosody over time. Tap a hotkey, speak, tap again, and the cleaned-up text
lands at your cursor about a second later.

> **macOS counterpart:** [`scdenney/macwhspr`](https://github.com/scdenney/macwhspr)
> ports this pipeline to Mac. Same `cleanup.py` prompt and `vocab.md` format,
> same `/hypr-calibrate` loop; Karabiner-Elements + Hammerspoon + a Python
> launchd daemon replace the Linux pieces. Triggered by the Globe/Fn key.

[Why](#why-use-this-setup) · [Trade-offs](#trade-offs) · [Contents](#repository-contents) · [Install](#install) · [OpenAI API setup](#openai-api-setup) · [Local options](#local-transcription-option) · [Calibration](#calibration-loop) · [Known issues](#known-issues-and-fixes)

---

The current version of this setup uses the OpenAI API for both transcription and
cleanup:

- hyprwhspr records audio from the microphone.
- OpenAI `gpt-realtime-whisper` transcribes speech to text over the Realtime
  WebSocket API (`wss://api.openai.com/v1/realtime?intent=transcription`) as
  audio streams in, rather than uploading a finished audio file after
  recording stops.
- A post-transcription hook sends the raw transcript to an LLM cleanup prompt.
- The hook logs raw and cleaned text pairs so the setup can be calibrated later.
- A Claude Code command, `/hypr-calibrate`, reviews those logs and updates the
  vocabulary/style file.

The batch REST endpoint (`gpt-4o-transcribe` via `/v1/audio/transcriptions`)
remains a supported fallback — see [OpenAI API setup](#openai-api-setup) below.

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
| OpenAI realtime transcription (`gpt-realtime-whisper`) + OpenAI cleanup | Lowest end-to-end latency (transcription streams while recording, mostly done by the time you stop talking), strong quality, no local GPU requirement | Sends audio/text to an API, ~3x the per-minute cost of the batch endpoint ($0.017/min vs $0.006/min), depends on network/API availability, WebSocket adds a bit more that can go wrong than a single REST call |
| OpenAI batch transcription (`gpt-4o-transcribe`) + OpenAI cleanup | Strong transcription quality, simplest setup (plain REST call), no local GPU requirement | Sends audio/text to an API, has usage cost, depends on network/API availability, full audio file uploads only after recording stops |
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

## Install

You need:

- Linux with [Hyprland](https://hypr.land) (this setup is tested under
  [Omarchy](https://omarchy.org))
- [hyprwhspr](https://github.com/goodroot/hyprwhspr) installed and working,
  following the upstream instructions
- An [OpenAI API key](https://platform.openai.com/api-keys)

Four steps: copy the files, fix two paths, add your key, start the service.

### 1. Clone and copy the config into place

```bash
git clone https://github.com/scdenney/hyperwhspr
cd hyperwhspr

mkdir -p ~/.config/hyprwhspr ~/.config/systemd/user ~/.claude/commands
cp config/config.json ~/.config/hyprwhspr/config.json
cp config/cleanup.py ~/.config/hyprwhspr/cleanup.py
cp config/vocab.md ~/.config/hyprwhspr/vocab.md
cp config/hyprwhspr.service ~/.config/systemd/user/hyprwhspr.service
cp claude/commands/hypr-calibrate.md ~/.claude/commands/hypr-calibrate.md
chmod +x ~/.config/hyprwhspr/cleanup.py
```

### 2. Point two paths at your machine

In `~/.config/hyprwhspr/config.json`, set the hook path to your real home
directory:

```json
"post_transcription_hook": "/home/YOUR_USER/.config/hyprwhspr/cleanup.py"
```

In the first line of `~/.config/hyprwhspr/cleanup.py`, set the shebang to
hyprwhspr's Python:

```python
#!/home/YOUR_USER/.local/share/hyprwhspr/venv/bin/python
```

### 3. Store your OpenAI API key and install the hook dependency

```bash
mkdir -p ~/.local/share/hyprwhspr
chmod 700 ~/.local/share/hyprwhspr
printf '{"openai":"YOUR_OPENAI_API_KEY"}\n' > ~/.local/share/hyprwhspr/credentials
chmod 600 ~/.local/share/hyprwhspr/credentials

~/.local/share/hyprwhspr/venv/bin/pip install httpx
```

### 4. Start the service

```bash
systemctl --user daemon-reload
systemctl --user enable --now hyprwhspr
systemctl --user status hyprwhspr
```

The status should read `active (running)`. Test it: focus any text field,
tap the hyprwhspr hotkey (`SUPER+ALT+D` by default), speak a sentence, tap
again. The cleaned-up text pastes at your cursor about a second after you
stop. If nothing pastes, check the log with
`journalctl --user -u hyprwhspr -f` and see
[Known issues](#known-issues-and-fixes).

Day-to-day service commands:

```bash
systemctl --user restart hyprwhspr
systemctl --user stop hyprwhspr
journalctl --user -u hyprwhspr -f
```

### Install with an agent

The steps above are written so a coding agent can run them. Paste this into
Claude Code or Codex:

```text
Install hyperwhspr from https://github.com/scdenney/hyperwhspr: clone the
repo and follow the README's Install section. If upstream hyprwhspr is not
installed, install it first from https://github.com/goodroot/hyprwhspr.
Substitute my real home directory for the YOUR_USER placeholders in step 2.
Skip the API key line in step 3; I will create the credentials file myself.
Finish by running `systemctl --user status hyprwhspr` and showing me the
result.
```

The agent handles the clone, file copies, path edits, dependency install, and
service setup. Create the credentials file yourself (the `printf` line in
step 3) so your API key never passes through the conversation.

## OpenAI API setup

The example config uses OpenAI's Realtime WebSocket transcription model,
`gpt-realtime-whisper`. OpenAI's audio docs describe the transcription
endpoints and the supported transcription models:
<https://platform.openai.com/docs/guides/speech-to-text>.

The API key lives in `~/.local/share/hyprwhspr/credentials` (created in
[Install](#install) step 3, outside git). The same credentials file is used
for both the `rest-api` and `realtime-ws` backends (the key is looked up by
provider name, `openai`, not by backend).

The relevant hyprwhspr config block is:

```json
{
  "transcription_backend": "realtime-ws",
  "websocket_provider": "openai",
  "websocket_model": "gpt-realtime-whisper",
  "websocket_url": null,
  "realtime_mode": "transcribe"
}
```

`whisper_prompt` does **not** apply under `realtime-ws` with
`gpt-realtime-whisper` — OpenAI's Realtime transcription sessions do not
support a `prompt`/vocabulary-steering field for this model (confirmed in
OpenAI's Realtime transcription guide: "For `gpt-realtime-whisper` in GA
Realtime sessions, `prompt` is not supported"). hyprwhspr builds an
`instructions` string from `whisper_prompt` and passes it to the client, but
`_send_session_update()` only includes `instructions` in the codebase's
`converse` (voice-to-AI) mode, not `transcribe` mode — so for our
`realtime_mode: "transcribe"` setup it is silently unused. Domain vocabulary
correction still happens downstream in the `cleanup.py` hook via `vocab.md`.
`gpt-realtime-whisper` only supports `realtime_mode: "transcribe"`.

### Batch REST fallback

The older batch endpoint (`gpt-4o-transcribe` via `/v1/audio/transcriptions`)
is still supported and can be simpler to reason about if the WebSocket
backend causes problems on a given network:

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

`gpt-4o-mini-transcribe` is a cheaper, lower-latency alternative on the same
REST path, at a documented accuracy trade-off versus `gpt-4o-transcribe`.

### Cleanup model

The cleanup hook defaults to `gpt-4.1-mini` through the OpenAI Chat Completions
API (its `httpx` dependency is installed in [Install](#install) step 3).
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
| 2026-07-13 | Evaluated newer OpenAI voice models; switched to realtime streaming transcription | Switched `transcription_backend` from `rest-api` to `realtime-ws` with `websocket_provider: "openai"`, `websocket_model: "gpt-realtime-whisper"`. Verified end to end: WebSocket connects on service start, transcript returned ~1s after recording stops, cleanup hook unaffected. Batch `gpt-4o-transcribe` REST config kept documented as a fallback |
| 2026-07-13 | Corrected inaccurate claim that `whisper_prompt` still applies under `realtime-ws` | Confirmed via source (`realtime_client.py`) and OpenAI's Realtime transcription guide that `gpt-realtime-whisper` does not support prompt/vocabulary steering at all in GA Realtime sessions; hyprwhspr builds the `instructions` string but never sends it in `transcribe` mode. Vocabulary correction now relies solely on the `cleanup.py` + `vocab.md` step |
| 2026-07-22 | After a realtime session hit OpenAI's 60-minute cap, every recording attempt failed instantly with `[ERROR] Realtime backend not connected yet`, no reconnect attempt logged | Root cause in `hyprwhspr` package 1.38.2-1 (`realtime_base.py`): the on-demand reconnect path calls `close()` right before `connect()`; `close()` sets `_closed = True` permanently, and `connect()`'s internal `_connect_internal()` bails out immediately whenever `_closed` is set, so it never even opens a socket. Patched `/usr/lib/hyprwhspr/lib/src/realtime_base.py` locally: `connect()` now resets `_closed` and rebuilds `_stop_event` before reconnecting. This patch lives outside the package manager and will be overwritten on the next `hyprwhspr` update — reapply after upgrading, or open a PR against `goodroot/hyprwhspr` |

## Security notes

- Do not commit `~/.local/share/hyprwhspr/credentials`.
- Do not commit `~/.config/hyprwhspr/cleanup_log.jsonl`; it may contain private
  dictated text.
- Review `vocab.md` before publishing if it includes personal names, project
  names, or sensitive vocabulary.
