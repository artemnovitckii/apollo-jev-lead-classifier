"""Minimal local key loading: no shell evaluation, interpolation, or dependencies."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEYS = ("APOLLO_API_KEY", "TYPESAFE_API_KEY")


def load_env(path=ROOT / ".env"):
    if not Path(path).exists():
        return
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if separator and name in KEYS:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if value and not os.environ.get(name):
                os.environ[name] = value
