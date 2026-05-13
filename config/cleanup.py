#!/home/buddleman/.local/share/hyprwhspr/venv/bin/python
"""
hyprwhspr post-transcription cleanup via GPT-4.1-mini.
Uses httpx directly (79ms import) instead of the openai SDK (440ms import).
Reads raw transcription from stdin, prints cleaned text to stdout.
Logs (raw, cleaned) pairs to cleanup_log.jsonl for /hypr-calibrate sessions.
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path
import httpx

CREDENTIALS_FILE = Path.home() / '.local/share/hyprwhspr/credentials'
VOCAB_FILE = Path.home() / '.config/hyprwhspr/vocab.md'
LOG_FILE = Path.home() / '.config/hyprwhspr/cleanup_log.jsonl'
MODEL = 'gpt-4.1-mini'
API_URL = 'https://api.openai.com/v1/chat/completions'

SYSTEM_PROMPT = (
    "You are a transcription cleanup assistant for an assistant professor working in "
    "programming research and academic communication. The input is raw speech-to-text output. "
    "Fix punctuation, capitalization, and grammar. Remove filler words, false starts, and "
    "speech disfluencies. Add paragraph breaks where appropriate. Format as a list when the "
    "content naturally calls for it. Produce text suitable for emails, research notes, or "
    "teaching materials. Preserve the speaker's exact meaning and tone. "
    "Output only the cleaned text — nothing else."
)


def api_key():
    return json.loads(CREDENTIALS_FILE.read_text())['openai']


def vocab_context():
    if VOCAB_FILE.exists():
        text = VOCAB_FILE.read_text().strip()
        if text:
            return f"\n\nVocabulary and style preferences:\n{text}"
    return ''


def clean(raw: str) -> str:
    key = api_key()
    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT + vocab_context()},
            {'role': 'user', 'content': raw},
        ],
        'max_tokens': 512,
        'temperature': 0.1,
    }
    resp = httpx.post(
        API_URL,
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        json=payload,
        timeout=4.0,
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content'].strip()


def log(raw: str, cleaned: str):
    entry = json.dumps({
        'ts': datetime.now(timezone.utc).isoformat(),
        'raw': raw,
        'cleaned': cleaned,
    })
    with LOG_FILE.open('a') as f:
        f.write(entry + '\n')


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return
    cleaned = clean(raw)
    print(cleaned, end='')
    log(raw, cleaned)


if __name__ == '__main__':
    main()
