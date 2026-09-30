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


def test_parallel_writes_do_not_corrupt_or_lose_entries(tmp_path):
    # The agent runs tool calls on parallel threads; this is the race that
    # corrupted data/task_log.json in a live run.
    from concurrent.futures import ThreadPoolExecutor

    log = TaskLog(path=str(tmp_path / "log.json"))
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda i: log.log_task(f"task {i}", priority="low"), range(40)))
        list(ex.map(lambda i: log.log_achievement(f"done {i}"), range(40)))

    assert len(log.list_open_tasks()) == 40
    assert len(log.list_recent_achievements(days=1)) == 40


def test_corrupt_file_is_set_aside_not_silently_overwritten(tmp_path):
    path = tmp_path / "log.json"
    path.write_text('{"tasks": {}, "achievements": {}}\n}\n}', encoding="utf-8")

    log = TaskLog(path=str(path))
    log.log_task("fresh start")

    backups = list(tmp_path.glob("log.json.corrupt-*"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8").endswith("}")
    assert [t["description"] for t in log.list_open_tasks()] == ["fresh start"]
