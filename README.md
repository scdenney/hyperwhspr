# hyperwhspr

[![platform](https://img.shields.io/badge/platform-Linux%20%2F%20Hyprland-FCC624?logo=linux&logoColor=black)](https://hypr.land)
[![upstream](https://img.shields.io/badge/upstream-hyprwhspr-8A2BE2)](https://github.com/goodroot/hyprwhspr)
[![transcription](https://img.shields.io/badge/transcription-gpt--live--transcribe-111111?logo=openai&logoColor=white)](https://platform.openai.com/docs/guides/speech-to-text)
[![updated](https://img.shields.io/badge/updated-September%202026-green)](https://github.com/scdenney/hyperwhspr/commits/master)
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
- OpenAI `gpt-live-transcribe` transcribes speech to text over the Realtime
  WebSocket API (`wss://api.openai.com/v1/realtime?intent=transcription`) as
  audio streams in, rather than uploading a finished audio file after
  recording stops. `whisper_prompt` is sent as the session prompt, so domain
  vocabulary steers transcription directly.
- A post-transcription hook sends the raw transcript to an LLM cleanup prompt.
- The hook logs raw and cleaned text pairs so the setup can be calibrated later.
- A Claude Code command, `/hypr-calibrate`, reviews those logs and updates the
  vocabulary/style file.

The batch REST endpoint (`gpt-transcribe` via `/v1/audio/transcriptions`)
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
| OpenAI realtime transcription (`gpt-live-transcribe`) + OpenAI cleanup | Lowest end-to-end latency (transcription streams while recording, mostly done by the time you stop talking), strong quality, no local GPU requirement | Sends audio/text to an API, ~3x the per-minute cost of the batch endpoint ($0.017/min vs $0.006/min), depends on network/API availability, WebSocket adds a bit more that can go wrong than a single REST call |
| OpenAI batch transcription (`gpt-transcribe`) + OpenAI cleanup | Strong transcription quality, simplest setup (plain REST call), no local GPU requirement | Sends audio/text to an API, has usage cost, depends on network/API availability, full audio file uploads only after recording stops |
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
`gpt-live-transcribe`. OpenAI's audio docs describe the transcription
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
  "websocket_model": "gpt-live-transcribe",
  "websocket_url": null,
  "realtime_mode": "transcribe",
  "realtime_transcription_delay": "low"
}
```

`whisper_prompt` **does** apply here. `gpt-realtime-whisper`, the previous
default, took no prompt at all in GA Realtime sessions; its successor
`gpt-live-transcribe` accepts `prompt`, `languages` and `delay` in the
transcription session, at the same price and the same latency. hyprwhspr
1.43 sends `whisper_prompt` as the session `prompt` for any model with the
`language_context` capability, so listing domain terms in `whisper_prompt`
steers transcription rather than leaving every proper noun to be repaired
afterwards by cleanup.

hyprwhspr has no `keywords` field, which is the stronger steering lever the
macOS counterpart uses. Terms the prompt alone does not fix stay in
`vocab.md` for the `cleanup.py` step. `gpt-live-transcribe` only supports
`realtime_mode: "transcribe"`.

`realtime_transcription_delay` trades latency against segment quality
(`minimal|low|medium|high|xhigh`). `low` is the default and what this setup
uses.

### Batch REST fallback

The batch endpoint (`gpt-transcribe` via `/v1/audio/transcriptions`)
is still supported and can be simpler to reason about if the WebSocket
backend causes problems on a given network:

```json
{
  "transcription_backend": "rest-api",
  "rest_endpoint_url": "https://api.openai.com/v1/audio/transcriptions",
  "rest_api_provider": "openai",
  "rest_api_key": null,
  "rest_headers": {},
  "rest_body": {"model": "gpt-transcribe"}
}
```

`gpt-4o-mini-transcribe` is a cheaper, lower-latency alternative on the same
REST path, at a documented accuracy trade-off versus `gpt-transcribe`.

### Cleanup model

The cleanup hook defaults to `gpt-5.4-mini` through the OpenAI Chat Completions
API (its `httpx` dependency is installed in [Install](#install) step 3).
You can override the cleanup model or endpoint with environment variables in the
service file:

```ini
Environment=HYPRWHSPR_CLEANUP_MODEL=gpt-5.4-mini
Environment=HYPRWHSPR_LLM_API_URL=https://api.openai.com/v1/chat/completions
```

Cleanup is the larger half of the post-stop wait, so the model choice matters
more for latency than the transcription model does. Benchmarked on three real
transcripts from `cleanup_log.jsonl` (93 / 275 / 1,833 chars, N=3 each, same
system prompt, min/median/max seconds, with the output length on the longest
case):

| Model | short | medium | long (1,833 ch) | long output |
| --- | --- | --- | --- | --- |
| `gpt-4.1-mini` (was) | 0.65/1.06/1.51 | 0.89/0.92/1.25 | 2.13/2.53/2.69 | 1,418 ch |
| `gpt-4.1-nano` | 0.67/1.02/1.04 | 0.79/0.80/0.82 | 1.87/1.94/2.17 | 1,586 ch |
| `gpt-5.4-nano` | 0.82/0.90/1.10 | 1.11/1.13/1.15 | 2.43/2.66/2.71 | 1,652 ch |
| `gpt-5.4-mini` (now) | 0.51/0.55/0.78 | 0.67/0.70/0.97 | 1.57/1.58/1.65 | 1,687 ch |

Read the outputs, not only the clock. `gpt-4.1-mini` was paraphrasing: on the
long case it returned 23% fewer characters than it was given and pushed
dictated first person into stiffer prose. `gpt-5.4-mini` is both the fastest
and the most faithful here, preserving length, paragraph breaks, and the
dictated voice. `reasoning_effort` is set to `none` — anything else puts
thinking tokens straight into the wait. The gpt-5 line renames `max_tokens` to
`max_completion_tokens` and rejects `temperature`, so `cleanup.py` branches on
the model name; non-gpt-5 models still get the old payload shape.

The macOS counterpart chose `gpt-5.4-nano` on the same benchmark. That is not
a contradiction: its dictations run to ~5,000 characters, where `gpt-5.4-mini`
starts under-paragraphing. Linux dictations here top out at 1,833, so that
failure mode does not bite. Re-run the benchmark against your own log before
copying either choice.

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
| 2026-08-12 | Same stalled-graph wedge as 2026-08-11 recurred (third episode in three days: Aug 10, 11, 12) | Root cause found one level deeper: wireplumber 0.5.15 leaks GObject weak references until it hits GLib's hard 65535 GWeakRef cap (`Too many GWeakRef registered` — 50k+ journal entries over two days), after which the session manager cannot route new capture streams and the pulse graph stalls. No fixed wireplumber package available yet. Durable fix: added `hyprwhspr-audio-watchdog.service` (user unit running `~/.config/hyprwhspr/audio_watchdog.sh`) that follows the wireplumber and hyprwhspr journals and self-heals — on the first `Too many GWeakRef` message it restarts `pipewire pipewire-pulse wireplumber` (hyprwhspr detects the pulse restart and self-recovers via its built-in `pulse_server_restart` recovery), and on the wedge signature (`Recording thread did not exit cleanly` / `Cleanup still owns the audio stream`) it also restarts hyprwhspr. 10-minute cooldown between heals. Snapshots in `config/` |
| 2026-08-12 | Transcribed text often not pasted into the focused window (observed in Ghostty running herdr); text was on the clipboard (manual Super+V worked) and hyprwhspr logged `[INJECT] Text injected` as if successful | Hyprland >= 0.55's `sendshortcut` dispatcher can silently no-op for some apps (Ghostty among them) while `hyprctl` still exits 0, and hyprwhspr's `_send_shortcut_hyprland` treats exit 0 as success, so the wtype fallback never fires. Patched `/usr/lib/hyprwhspr/lib/src/text_injector.py` to prefer wtype's virtual-keyboard path on Hyprland with `sendshortcut` as the fallback. Patch script kept at `~/.config/hyprwhspr/patch_wtype_first.py` (run with sudo); like the realtime_base.py patch it lives outside the package manager and must be reapplied after a hyprwhspr upgrade |
| 2026-08-11 | Recording silently wedged: every attempt logged `[WARN] Recording thread did not exit cleanly after 3 seconds` then `[RECOVERY] Cleanup still owns the audio stream; recording refused`, requiring a service restart to clear | Root cause was one level below hyprwhspr: the PipeWire graph had stalled — ALSA (`arecord -D hw:0,0`) captured real audio fine and the mic showed unmuted at 100% in `amixer`, but the PulseAudio-compatible pulse layer (`parecord`) produced only a 44-byte WAV header, i.e. zero audio bytes. hyprwhspr's `audio_capture.py` opens the input stream via `sounddevice`/PortAudio with no timeout, so against a stalled pulse graph the open call blocks forever and the recording thread never reaches its cleanup `finally` block, wedging `_cleanup_complete` permanently. Fix: `systemctl --user restart pipewire pipewire-pulse wireplumber`, then `systemctl --user restart hyprwhspr`; verified with a real start/stop/transcribe cycle afterward. `systemctl --user restart hyprwhspr` alone does not clear this — the stall is in the audio graph, not the hyprwhspr process. hyprwhspr itself still has no timeout around the stream-open call, so a stalled pulse graph will keep wedging it this way until that gets a timeout upstream |
| 2026-09-13 | First hotkey press after every boot did nothing; a second press was needed to start recording | hyprwhspr opens the Realtime WebSocket once at startup and lost the race with DHCP/DNS: the journal showed `[REALTIME] WebSocket error: [Errno -3] Temporary failure in name resolution` at 10:28:06 against NetworkManager's DHCP lease and DNS at 10:28:07, then `[ERROR] Failed to initialize backend - will retry on next record attempt`. Upstream only retries on the next record attempt, so the first press was consumed by `[CONTROL] Recording blocked: backend init failed - retrying` and the recording never started. Added an `ExecStartPre` to the service that waits (bounded at 30s) for `api.openai.com` to resolve before `ExecStart`, skipped when the config uses a local backend |
| 2026-09-13 | Transcription mangled every domain term (`HyperWhisper`, `Hyperland`, `Olmarky`, `Carabiner`), leaving cleanup to guess | Switched `websocket_model` from `gpt-realtime-whisper` to `gpt-live-transcribe`, which accepts a session `prompt`; hyprwhspr 1.43 sends `whisper_prompt` for models with the `language_context` capability. Domain terms added to `whisper_prompt`. Measured on a fixed TTS clip streamed at 1x: `Hyprland`, `omarchy`, `Karabiner` and `ydotool` all come back correct, at 1.33s commit-to-final against 1.29s unsteered. `hyprwhspr` and `macwhspr` themselves still need the `cleanup.py` + `vocab.md` repair, since hyprwhspr has no `keywords` field. Also corrected the standing README claim that `whisper_prompt` cannot apply under `realtime-ws` — true of `gpt-realtime-whisper`, not of its successor |
| 2026-09-13 | Cleanup was paraphrasing rather than reformatting, and was the larger half of the post-stop wait | Moved the cleanup default from `gpt-4.1-mini` to `gpt-5.4-mini` with `reasoning_effort: none`, raised `max_tokens` 512 -> 4096 and the timeout 4s -> 12s. On the longest real transcript in the log `gpt-4.1-mini` returned 1,418 characters against 1,687 for `gpt-5.4-mini`, and took 2.53s against 1.58s. `cleanup.py` now branches its payload on the model name, since the gpt-5 line renamed `max_tokens` and rejects `temperature`. Benchmark table under [Cleanup model](#cleanup-model) |

## Security notes

- Do not commit `~/.local/share/hyprwhspr/credentials`.
- Do not commit `~/.config/hyprwhspr/cleanup_log.jsonl`; it may contain private
  dictated text.
- Review `vocab.md` before publishing if it includes personal names, project
  names, or sensitive vocabulary.
