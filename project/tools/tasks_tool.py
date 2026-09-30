"""
Real Google Tasks API calls — writes follow-up items into the parent's own
"My Tasks" list (the one shown in Gmail's and Calendar's Tasks side panel
and the Google Tasks mobile app), kept in due-date order, plus two daily
summary tasks in a separate list.

Google Tasks titles are plain text — no priority, color, or font-size
field — so priority is carried as a label at the front of the title
("🔴 [HIGH] ...", visible everywhere the task shows up), with the agent's
reason for choosing it in the notes.
"""
from __future__ import annotations

from datetime import date

TASKLIST = "@default"  # "My Tasks"
SUMMARY_LIST_TITLE = "MyAgent Daily Summary"

PRIORITY_MARKERS = {
    "high": "🔴",
    "medium": "🟠",
    "low": "🟢",
}

SUMMARY_KINDS = {
    "start": "☀️ Start of day",
    "end": "🌙 End of day",
}

NOTES_LIMIT = 8000  # Google Tasks caps notes at 8192 characters


def normalize_priority(priority: str | None) -> str:
    p = (priority or "medium").strip().lower()
    return p if p in PRIORITY_MARKERS else "medium"


def priority_label(priority: str) -> str:
    priority = normalize_priority(priority)
    return f"{PRIORITY_MARKERS[priority]} [{priority.upper()}]"


def _strip_label(title: str) -> str:
    title = title.strip()
    for priority, marker in PRIORITY_MARKERS.items():
        for prefix in (f"{marker} [{priority.upper()}]", marker):
            if title.startswith(prefix):
                return title[len(prefix):].strip()
    return title


def _due(due_date: str) -> str:
    return f"{date.fromisoformat(due_date).isoformat()}T00:00:00.000Z"


def _list_all(tasks_service, tasklist: str, show_completed: bool = False) -> list[dict]:
    """Every task in a list, in the order Google shows it."""
    items, page_token = [], None
    while True:
        response = (
            tasks_service.tasks()
            .list(
                tasklist=tasklist,
                showCompleted=show_completed,
                showHidden=show_completed,
                maxResults=100,
                pageToken=page_token,
            )
            .execute()
        )
        items.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return sorted(items, key=lambda t: t.get("position", ""))


def find_open_task(tasks_service, title: str) -> dict | None:
    """Return an open task in My Tasks whose title matches (ignoring the
    priority label and case), so re-runs don't create duplicates."""
    wanted = _strip_label(title).casefold()
    for item in _list_all(tasks_service, TASKLIST):
        if _strip_label(item.get("title", "")).casefold() == wanted:
            return item
    return None


def _previous_for(tasks_service, due: str | None) -> str | None:
    """Pick where a new task goes so My Tasks reads in due-date order: right
    after the last open task due on or before it (undated tasks go last).
    None means the top of the list."""
    previous = None
    for item in _list_all(tasks_service, TASKLIST):
        item_due = item.get("due")
        if due is None or (item_due is not None and item_due[:10] <= due[:10]):
            previous = item["id"]
    return previous


def create_task(
    tasks_service, title: str, priority: str, due_date: str | None = None, priority_reason: str = ""
) -> str:
    """Create a task in My Tasks, in due-date order, and return its ID.
    `due_date` is YYYY-MM-DD; Google Tasks stores dates only."""
    priority = normalize_priority(priority)
    reason = f" — {priority_reason.strip()}" if priority_reason.strip() else ""
    body = {
        "title": f"{priority_label(priority)} {title.strip()}",
        "notes": f"Priority: {priority.capitalize()}{reason}\n\n[Created by MyAgent]",
    }
    if due_date:
        body["due"] = _due(due_date)
    previous = _previous_for(tasks_service, body.get("due"))
    kwargs = {"previous": previous} if previous else {}
    created = tasks_service.tasks().insert(tasklist=TASKLIST, body=body, **kwargs).execute()
    return created["id"]


def complete_task(tasks_service, task_id: str) -> None:
    tasks_service.tasks().patch(tasklist=TASKLIST, task=task_id, body={"status": "completed"}).execute()


def _summary_list_id(tasks_service) -> str:
    response = tasks_service.tasklists().list(maxResults=100).execute()
    for item in response.get("items", []):
        if item["title"] == SUMMARY_LIST_TITLE:
            return item["id"]
    return tasks_service.tasklists().insert(body={"title": SUMMARY_LIST_TITLE}).execute()["id"]


def upsert_daily_summary(tasks_service, kind: str, summary: str, today: date) -> str:
    """Write the start- or end-of-day summary into its own list, updating the
    same task every day rather than piling up a new one each run."""
    prefix = SUMMARY_KINDS[kind]
    list_id = _summary_list_id(tasks_service)
    body = {
        "title": f"{prefix} · {today:%a %b} {today.day}",
        "notes": summary.strip()[:NOTES_LIMIT],
        "due": _due(today.isoformat()),
        "status": "needsAction",
    }
    existing = _list_all(tasks_service, list_id, show_completed=True)
    for item in existing:
        if item.get("title", "").startswith(prefix):
            tasks_service.tasks().patch(tasklist=list_id, task=item["id"], body=body).execute()
            return item["id"]
    # Append, so "Start of day" (written first) stays above "End of day".
    kwargs = {"previous": existing[-1]["id"]} if existing else {}
    return tasks_service.tasks().insert(tasklist=list_id, body=body, **kwargs).execute()["id"]
