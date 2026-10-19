"""A tiny append-only response cache, so reruns are free and runs are auditable.

Keyed by a hash of everything that determines a response (model, prompt version,
repeat index, input text). Failures are never stored: only a successful raw
response is cached, so a timeout cannot be replayed as if it were an answer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def make_key(*parts: object) -> str:
    joined = "\x1f".join(str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._data: dict[str, str] = {}
        if path is not None and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._data[row["key"]] = row["value"]

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def put(self, key: str, value: str) -> None:
        self._data[key] = value
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps({"key": key, "value": value}) + "\n")

    def __len__(self) -> int:
        return len(self._data)
