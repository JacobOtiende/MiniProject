"""
Safe load/save for the small JSON files the agent keeps in data/.

The agent runs parallel tool calls on worker threads, so two writes can
land at once. Callers hold a lock around each read-modify-write; this
module makes each write atomic (temp file + rename, so a reader never sees
a half-written file) and never silently discards a file it can't parse —
a corrupt file is set aside for inspection instead of being overwritten.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable


def load(path: str, empty: Callable[[], Any]) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return empty()
    if not content.strip():
        return empty()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        backup = f"{path}.corrupt-{datetime.now():%Y%m%d-%H%M%S}"
        os.replace(path, backup)
        print(f"Warning: {path} was unreadable; moved it to {backup} and started fresh.")
        return empty()


def save(path: str, data: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
