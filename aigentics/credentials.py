"""Explicit credential loading; no plaintext credential persistence."""

import os
import re
import threading
from pathlib import Path


class Credentials:
    def __init__(self):
        self._lock = threading.RLock()
        self._values = {}
        self._referenced = set()
        for name, value in os.environ.items():
            if re.search(r"(KEY|TOKEN|SECRET|PASSWORD)$", name, re.I) and len(value) >= 6:
                self._values[name] = value

    def load_env(self, path: Path):
        from dotenv import dotenv_values

        if not path.is_file() or path.stat().st_size > 1_000_000:
            raise ValueError("Select a .env file smaller than 1 MB")
        values = dotenv_values(path, encoding="utf-8-sig", interpolate=False)
        with self._lock:
            self._values.update({k: v for k, v in values.items() if v})
        return sorted(k for k, v in values.items() if v)

    def names(self):
        with self._lock:
            return set(self._values)

    def get(self, ref: str):
        if not ref:
            return ""
        with self._lock:
            self._referenced.add(ref)
            if ref in self._values:
                return self._values[ref]
        import keyring

        value = keyring.get_password("aigentics-desktop", ref)
        if not value:
            raise ValueError(
                f"Credential reference '{ref}' is not available. Load your .env or save it in the OS vault."
            )
        with self._lock:
            self._values[ref] = value
            self._referenced.add(ref)
        return value

    def save(self, ref: str, value: str):
        if not ref or len(value) < 6:
            raise ValueError("Provide a credential reference and a key of at least six characters")
        import keyring

        # Fail visibly if no OS credential service is available. Never fall back to a text file.
        keyring.set_password("aigentics-desktop", ref, value)
        with self._lock:
            self._values[ref] = value
            self._referenced.add(ref)

    def scrub(self, value):
        if isinstance(value, dict):
            return {
                key: "[REDACTED]"
                if str(key).lower() in {"api_key", "apikey", "password", "secret", "token", "authorization"}
                else self.scrub(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self.scrub(item) for item in value]
        return self.redact(value) if isinstance(value, str) else value

    def json(self, value, **kwargs):
        import json

        return json.dumps(self.scrub(value), **kwargs)

    def redact(self, value):
        if not isinstance(value, str):
            return self.json(value, ensure_ascii=False)
        text = value
        with self._lock:
            values = sorted(
                {
                    v
                    for k, v in self._values.items()
                    if k in self._referenced or re.search(r"(KEY|TOKEN|SECRET|PASSWORD)$", k, re.I)
                },
                key=len,
                reverse=True,
            )
        for secret in values:
            if secret:
                text = text.replace(secret, "[REDACTED]")
        text = re.sub(r"(?i)(bearer\s+)[\w.\-]+", r"\1[REDACTED]", text)
        text = re.sub(r"\b(?:sk-|gsk_)[A-Za-z0-9_\-]{8,}", "[REDACTED]", text)
        text = re.sub(r"(?i)((?:api[_-]?key|password|token|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", text)
        return text
