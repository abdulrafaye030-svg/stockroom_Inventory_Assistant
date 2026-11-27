"""Load settings from a local .env file into os.environ (no extra packages needed).

Lines look like KEY=value. Blank lines and lines starting with # are skipped, an
optional leading "export " is allowed, and matching quotes around a value are removed.
Variables that are already set (for example in Vercel's settings) are never overwritten.
"""
import os
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / ".env"


def parse_env(text):
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_env_file(path=DEFAULT_PATH):
    """Apply the file's values to os.environ and return them; a missing file is fine."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return {}
    values = parse_env(text)
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values
