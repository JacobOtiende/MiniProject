from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.deps import Deps
from agent.tools import sync_unsynced_tasks
from tasks.task_log import TaskLog
from tools import tasks_tool
from tools.demo_tasks import InMemoryTasksService


def test_my_tasks_stay_in_due_date_order_with_undated_last():
    service = InMemoryTasksService()
    tasks_tool.create_task(service, "Oct 10 thing", "low", "2026-10-10")
    tasks_tool.create_task(service, "No date thing", "low")
    tasks_tool.create_task(service, "Oct 2 thing", "high", "2026-10-02")
    tasks_tool.create_task(service, "Oct 6 thing", "medium", "2026-10-06")
    tasks_tool.create_task(service, "Oct 6 second", "low", "2026-10-06")

    assert service.titles() == [
        "🔴 [HIGH] Oct 2 thing",
        "🟠 [MEDIUM] Oct 6 thing",
        "🟢 [LOW] Oct 6 second",
        "🟢 [LOW] Oct 10 thing",
        "🟢 [LOW] No date thing",
    ]


def test_daily_summaries_live_in_their_own_list_and_update_in_place():
    service = InMemoryTasksService()
    tasks_tool.upsert_daily_summary(service, "start", "- Parent night at 6pm", date(2026, 9, 30))
    tasks_tool.upsert_daily_summary(service, "end", "- Queued RSVP", date(2026, 9, 30))
    # Next day: same two tasks, refreshed, not four.
    tasks_tool.upsert_daily_summary(service, "start", "- Shelf Buddies due", date(2026, 10, 1))

    [summary_list] = [k for k, v in service.list_titles.items() if v == tasks_tool.SUMMARY_LIST_TITLE]
    tasks = service.lists[summary_list]
    assert [t["title"] for t in tasks] == ["☀️ Start of day · Thu Oct 1", "🌙 End of day · Wed Sep 30"]
    start = next(t for t in tasks if t["title"].startswith("☀️"))
    assert start["notes"] == "- Shelf Buddies due" and start["due"] == "2026-10-01T00:00:00.000Z"
    assert service.titles() == []  # nothing added to My Tasks


def test_tasks_logged_while_google_was_unavailable_are_synced_later(tmp_path):
    task_log = TaskLog(path=str(tmp_path / "log.json"))
    task_log.log_task("Submit Shelf Buddies application", "2026-10-04", "high", priority_reason="Starts Oct 5.")
    deps = Deps(mode="demo", model=None, calendar_service=None, calendar_id="primary",
                approval_queue=None, task_log=task_log, tasks_service=InMemoryTasksService())

    assert sync_unsynced_tasks(deps) == 1
    assert sync_unsynced_tasks(deps) == 0  # already synced; no duplicate
    [google_task] = deps.tasks_service.lists["@default"]
    assert google_task["title"] == "🔴 [HIGH] Submit Shelf Buddies application"
    assert google_task["notes"].startswith("Priority: High — Starts Oct 5.")
    assert task_log.list_open_tasks()[0]["google_task_id"] == google_task["id"]
