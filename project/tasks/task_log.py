"""
Persistent memory for the single agent: open tasks it's tracking across
runs, and a log of things it (or you) marked as done. This is what lets a
"give me a rundown" or "what got accomplished" request mean something —
without it, every invocation starts blank and the agent has no history to
summarize.

Same JSON-backed pattern as approvals/approval_queue.py, deliberately: one
disk-backed store per concern, no shared global state.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any


class TaskLog:
    def __init__(self, path: str = "./data/task_log.json"):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.exists(path):
            self._save({"tasks": {}, "achievements": {}})

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.path) as f:
                content = f.read()
                if not content.strip():
                    return {"tasks": {}, "achievements": {}}
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"tasks": {}, "achievements": {}}

    def _save(self, data: dict[str, Any]) -> None:
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    # --- tasks ---

    def log_task(self, description: str, due_date: str | None = None) -> str:
        data = self._load()
        task_id = str(uuid.uuid4())[:8]
        data["tasks"][task_id] = {
            "description": description,
            "due_date": due_date,
            "status": "open",
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save(data)
        return task_id

    def list_open_tasks(self) -> list[dict]:
        data = self._load()
        return [{"task_id": k, **v} for k, v in data["tasks"].items() if v["status"] == "open"]

    def mark_task_done(self, task_id: str) -> bool:
        data = self._load()
        if task_id not in data["tasks"]:
            return False
        data["tasks"][task_id]["status"] = "done"
        data["tasks"][task_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._save(data)
        return True

    # --- achievements ---

    def log_achievement(self, description: str) -> str:
        data = self._load()
        achievement_id = str(uuid.uuid4())[:8]
        data["achievements"][achievement_id] = {
            "description": description,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save(data)
        return achievement_id

    def list_recent_achievements(self, days: int = 1) -> list[dict]:
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        data = self._load()
        recent = []
        for k, v in data["achievements"].items():
            logged_at = datetime.fromisoformat(v["logged_at"])
            if logged_at >= cutoff:
                recent.append({"achievement_id": k, **v})
        return recent
