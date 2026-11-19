#!/usr/bin/env python3
"""Patch hyprwhspr whisper_manager.py: retry truncated realtime transcripts via REST.

gpt-live-transcribe sometimes returns a complete-looking but partial
transcript (about 5-7 chars/s of audio against a normal 13-18) although the
full recording was streamed. hyprwhspr injects it as if it were whole. This
re-transcribes the same audio through the rest-api backend when a recording
of at least `short_transcript_min_seconds` (15) comes back under
`short_transcript_min_cps` (8), and keeps the longer transcript.

Debug: with "keep_last_recording": true in config.json, the last recording is
saved as ~/.config/hyprwhspr/last_recording.wav plus last_recording.json with
the realtime and REST transcripts (REST runs in the background when no retry
was needed, so injection is not delayed).

Ported from macwhspr (2026-11-19). Run with:
    sudo python3 ~/.config/hyprwhspr/patch_realtime_rest_retry.py
Reapply after any hyprwhspr package upgrade (like patch_wtype_first.py).
An optional path argument patches a different copy (for testing).
"""
import shutil
import sys

TARGET = sys.argv[1] if len(sys.argv) > 1 else "/usr/lib/hyprwhspr/lib/src/whisper_manager.py"
MARKER = "_local_realtime_retry"

OLD_CALL = """                log('[REALTIME] Backend not initialized')
                return ""
            return active.transcribe(audio_data, sample_rate, language_override=language_override)
"""

NEW_CALL = """                log('[REALTIME] Backend not initialized')
                return ""
            text = active.transcribe(audio_data, sample_rate, language_override=language_override)
            # Local patch (2026-11-19): realtime can return a partial transcript;
            # retry suspiciously short ones via REST. See patch_realtime_rest_retry.py.
            return self._local_realtime_retry(text, audio_data, sample_rate, language_override)
"""

OLD_ANCHOR = """    def _ensure_backend_fresh_locked(self, backend: str) -> bool:
"""

NEW_METHODS = '''    def _local_realtime_retry(self, text, audio_data, sample_rate, language_override):
        """Local patch: re-transcribe via REST when realtime output looks truncated."""
        text = text or ""
        rate = float(sample_rate or 16000)
        seconds = len(audio_data) / rate
        try:
            min_seconds = float(self.config.get_setting('short_transcript_min_seconds', 15))
            min_cps = float(self.config.get_setting('short_transcript_min_cps', 8))
        except (TypeError, ValueError):
            min_seconds, min_cps = 15.0, 8.0
        cps = len(text) / seconds if seconds else 0.0
        rest_text = None
        if seconds >= min_seconds and cps < min_cps:
            log(f'[REALTIME] Transcript looks truncated ({len(text)} chars for '
                f'{seconds:.1f}s = {cps:.1f} chars/s); retrying via REST')
            try:
                rest_text = self._local_rest_transcribe(audio_data, sample_rate, language_override)
                log(f'[REALTIME] REST retry: {len(rest_text)} chars (realtime had {len(text)})')
            except Exception as e:
                log(f'[REALTIME] REST retry failed, keeping realtime transcript: {e}')
        if str(self.config.get_setting('keep_last_recording', False)).lower() == 'true':
            self._local_save_last_recording(audio_data, sample_rate, language_override,
                                            text, rest_text, seconds)
        if rest_text and len(rest_text) > len(text):
            return rest_text
        return text

    def _local_rest_transcribe(self, audio_data, sample_rate, language_override):
        rest = BACKENDS['rest-api'](self)
        return (rest.transcribe(audio_data, sample_rate, language_override=language_override) or '').strip()

    def _local_save_last_recording(self, audio_data, sample_rate, language_override,
                                   realtime_text, rest_text, seconds):
        """Local patch debug aid: keep the latest recording and both transcripts."""
        import json
        import os
        import wave
        base = os.path.expanduser('~/.config/hyprwhspr')
        wav_path = os.path.join(base, 'last_recording.wav')
        json_path = os.path.join(base, 'last_recording.json')
        record = {
            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'seconds': round(seconds, 2),
            'realtime': realtime_text,
            'rest': rest_text,
        }

        def write_json():
            with open(json_path, 'w') as f:
                json.dump(record, f, indent=2, ensure_ascii=False)

        def rest_in_background():
            try:
                record['rest'] = self._local_rest_transcribe(audio_data, sample_rate, language_override)
            except Exception as e:
                record['rest'] = f'<REST failed: {e}>'
            write_json()

        try:
            pcm = (np.clip(audio_data, -1.0, 1.0) * 32767).astype('<i2').tobytes()
            with wave.open(wav_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(int(sample_rate or 16000))
                wf.writeframes(pcm)
            write_json()
            if rest_text is None:
                threading.Thread(target=rest_in_background, daemon=True).start()
            log('[REALTIME] Saved last_recording.wav/.json')
        except Exception as e:
            log(f'[REALTIME] Could not save last recording: {e}')

    def _ensure_backend_fresh_locked(self, backend: str) -> bool:
'''

src = open(TARGET).read()
if MARKER in src:
    print("Already patched - nothing to do.")
    sys.exit(0)
if src.count(OLD_CALL) != 1 or src.count(OLD_ANCHOR) != 1:
    print("ERROR: expected code blocks not found (package changed?); aborting, file untouched.")
    sys.exit(1)
shutil.copy2(TARGET, TARGET + ".bak-rest-retry")
src = src.replace(OLD_CALL, NEW_CALL, 1).replace(OLD_ANCHOR, NEW_METHODS, 1)
open(TARGET, "w").write(src)
print(f"Patched {TARGET} (backup at {TARGET}.bak-rest-retry)")
print("Now run: systemctl --user restart hyprwhspr")
