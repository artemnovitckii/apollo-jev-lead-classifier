"""Run this yourself in a terminal to enter API keys privately."""
import getpass
import os
from pathlib import Path

from local_settings import ROOT, KEYS


def main():
    target = ROOT / ".env"
    if target.exists():
        print("A .env file already exists. Edit it locally to change keys; existing values were preserved.")
        return
    print("Enter keys in this terminal, not in an AI chat. Input is hidden.")
    values = {key: getpass.getpass(f"{key} (Enter to skip): ").strip() for key in KEYS}
    if any("\n" in value or "\r" in value for value in values.values()):
        raise ValueError("Keys must each be a single line.")
    if not any(values.values()):
        print("No keys entered. Nothing saved.")
        return
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# Local credentials. Ignored by Git.\n")
        for key, value in values.items():
            f.write(f"{key}={value}\n")
    print("Saved keys locally to .env. Next: python3 lead_classifier.py --doctor")


if __name__ == "__main__":
    main()
