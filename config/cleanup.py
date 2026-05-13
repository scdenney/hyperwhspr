#!/home/buddleman/.local/share/hyprwhspr/venv/bin/python
"""
hyprwhspr post-transcription cleanup via GPT-4.1-mini.
Reads raw transcription from stdin, prints cleaned text to stdout.
Logs (raw, cleaned) pairs to cleanup_log.jsonl for /hypr-calibrate sessions.
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

CREDENTIALS_FILE = Path.home() / '.local/share/hyprwhspr/credentials'
VOCAB_FILE = Path.home() / '.config/hyprwhspr/vocab.md'
LOG_FILE = Path.home() / '.config/hyprwhspr/cleanup_log.jsonl'
MODEL = 'gpt-4.1-mini'

SYSTEM_PROMPT = (
    "You are a transcription cleanup assistant. The input is raw speech-to-text output. "
    "Fix punctuation, capitalization, and grammar. Remove any remaining filler or false starts. "
    "Preserve the speaker's exact meaning and tone. Output only the cleaned text — nothing else."
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
    from openai import OpenAI
    client = OpenAI(api_key=api_key())
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT + vocab_context()},
            {'role': 'user', 'content': raw},
        ],
        max_tokens=512,
        temperature=0.1,
    )
    return resp.choices[0].message.content.strip()


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
