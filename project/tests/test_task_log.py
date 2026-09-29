from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tasks.task_log import TaskLog


def test_task_lifecycle(tmp_path):
    log = TaskLog(path=str(tmp_path / "log.json"))
    task_id = log.log_task("Return field trip form", due_date="2026-10-02")

    open_tasks = log.list_open_tasks()
    assert len(open_tasks) == 1
    assert open_tasks[0]["description"] == "Return field trip form"

    assert log.mark_task_done(task_id) is True
    assert log.list_open_tasks() == []
    # Marking a nonexistent task is a clean False, not an exception.
    assert log.mark_task_done("does-not-exist") is False


def test_achievements_respect_recency_window(tmp_path):
    import json
    from datetime import datetime, timedelta, timezone

    log = TaskLog(path=str(tmp_path / "log.json"))
    log.log_achievement("Did something today")

    # Backdate a second achievement well outside a 1-day window.
    data = log._load()
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    data["achievements"]["old1"] = {"description": "Did something long ago", "logged_at": old_time}
    log._save(data)

    recent = log.list_recent_achievements(days=1)
    assert [a["description"] for a in recent] == ["Did something today"]
    assert len(log.list_recent_achievements(days=30)) == 2
