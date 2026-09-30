"""
The single agent's toolbelt. Every function here is a real capability
(real Gmail/Calendar calls in live mode, real in-memory stores in demo
mode) wrapped as a LangChain tool the model can call. The model decides
which of these to use, in what order — this module just executes whatever
it picks.

build_tools(deps) is a factory rather than module-level @tool functions
because each tool needs to close over the specific service objects/queues
in `deps` (there's no other clean way to hand a live googleapiclient
service or a per-run ApprovalQueue into a LangChain tool's call signature).
"""
from __future__ import annotations

import functools
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from langchain_core.tools import tool

from tools import calendar_tool, gmail_tool, tasks_tool


def _serialize(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        d = asdict(obj)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d
    return obj


def _report_errors(func):
    """A failing tool (API outage, bad argument) should be reported back to
    the model, not abort the whole run — so it can skip that item, leave the
    email unread for next time, and carry on with the rest."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return (
                f"Error: {type(e).__name__}: {e}. This action did not happen. "
                "If it was for an email, log_task what still needs doing so it isn't lost."
            )

    return wrapper


def _mark_read(deps, message_id: str) -> None:
    if deps.mode == "demo":
        deps.email_store.mark_read(message_id)
    else:
        gmail_tool.mark_as_read(deps.gmail_service, message_id)
    deps.read_email_ids.add(message_id)


def mark_remaining_emails_read(deps) -> int:
    """After triage, mark every school email the agent was shown as read in
    Gmail, including any it forgot to mark itself. Returns how many."""
    remaining = deps.seen_email_ids - deps.read_email_ids
    for message_id in remaining:
        _mark_read(deps, message_id)
    return len(remaining)


def sync_unsynced_tasks(deps) -> int:
    """Push open local tasks that never reached Google Tasks (e.g. logged
    while the API was unavailable) into My Tasks. Returns how many."""
    if deps.tasks_service is None:
        return 0
    synced = 0
    for task in deps.task_log.list_open_tasks():
        if task.get("google_task_id"):
            continue
        existing = tasks_tool.find_open_task(deps.tasks_service, task["description"])
        google_task_id = existing["id"] if existing else tasks_tool.create_task(
            deps.tasks_service,
            task["description"],
            task.get("priority") or "medium",
            task.get("due_date"),
            task.get("priority_reason") or "",
        )
        deps.task_log.set_google_task_id(task["task_id"], google_task_id)
        synced += 1
    return synced


def build_tools(deps):
    def _today_bounds() -> tuple[str, str]:
        today = deps.now()
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start.isoformat(), end.isoformat()

    @tool
    def list_new_school_emails() -> list[dict]:
        """List unread school emails that have arrived since you last checked.
        Use this to find new items needing triage (classify, decide on an
        action, act on it)."""
        if deps.mode == "demo":
            emails = deps.email_store.fetch_new()
        else:
            emails = gmail_tool.fetch_new_school_emails(deps.gmail_service, deps.school_sender_allowlist)
        # Only these can be marked read — the agent can't touch anything else in the inbox.
        deps.seen_email_ids.update(e.message_id for e in emails)
        return [_serialize(e) for e in emails]

    @tool
    def mark_email_read(message_id: str) -> str:
        """Mark a school email as read once you are completely done with it
        (every event, task, and reply it needed is taken care of, or you
        decided it needs nothing). It then won't come back on the next run."""
        if message_id not in deps.seen_email_ids:
            return f"Not marked: {message_id!r} is not one of the new school emails you listed this run."
        _mark_read(deps, message_id)
        return f"Marked {message_id} as read."

    @tool
    def list_recent_school_emails(days: int = 1) -> list[dict]:
        """List ALL school emails (read or unread) from the last `days` days.
        Use this for a daily rundown or an achievement summary, where you
        need the full recent picture rather than only what's still unread."""
        if deps.mode == "demo":
            since = deps.now() - timedelta(days=days)
            return [_serialize(e) for e in deps.email_store.fetch_recent(since)]
        since_iso = (deps.now() - timedelta(days=days)).isoformat()
        emails = gmail_tool.fetch_recent_school_emails(deps.gmail_service, deps.school_sender_allowlist, since_iso)
        return [_serialize(e) for e in emails]

    @tool
    def list_todays_calendar_events() -> list[dict]:
        """List everything already on the calendar for today. Use this to
        build a daily rundown."""
        start, end = _today_bounds()
        events = calendar_tool.list_events(deps.calendar_service, deps.calendar_id, start, end)
        return [_serialize(e) for e in events]

    @tool
    def check_calendar_conflict(start_iso: str, end_iso: str) -> list[dict]:
        """Check whether a proposed [start_iso, end_iso) window collides with
        anything already on the calendar. Always call this before
        create_calendar_event."""
        events = calendar_tool.check_conflict(deps.calendar_service, deps.calendar_id, start_iso, end_iso)
        return [_serialize(e) for e in events]

    @tool
    def propose_alternate_times(desired_start_iso: str, duration_minutes: int = 60) -> list[str]:
        """Find up to 3 conflict-free alternate start times near a desired
        time. Use this yourself to resolve a scheduling conflict before
        involving the parent — only log_task if nothing reasonable turns up."""
        return calendar_tool.propose_alternates(
            deps.calendar_service, deps.calendar_id, desired_start_iso, duration_minutes
        )

    @tool
    def create_calendar_event(title: str, start_iso: str, end_iso: str, description: str = "") -> str:
        """Create a real calendar event. Only call this after checking for
        conflicts with check_calendar_conflict."""
        return calendar_tool.create_event(
            deps.calendar_service, deps.calendar_id, title, start_iso, end_iso, description, source_agent="MyAgent"
        )

    @tool
    def queue_email_for_approval(to: str, subject: str, body: str) -> str:
        """Draft an email reply and queue it for the parent's explicit
        approval. This is the ONLY way a reply can ever be sent — there is
        no tool that sends directly, and you must never claim otherwise."""
        return deps.approval_queue.enqueue({"to": to, "subject": subject, "body": body})

    @tool
    def log_task(
        description: str, priority: str, priority_reason: str, due_date: Optional[str] = None
    ) -> str:
        """Log something that needs follow-through but isn't resolved yet.
        It is added to the parent's Google "My Tasks" list with a priority
        label ("🔴 [HIGH]", "🟠 [MEDIUM]", "🟢 [LOW]"), and remembered on your next run.

        description: short, action-first title, e.g. "Submit Shelf Buddies application".
        priority: "high", "medium", or "low" — your own judgment call.
        priority_reason: one short line on why you chose that priority.
        due_date: YYYY-MM-DD — the deadline, or the date the action must be done by.
        """
        priority = tasks_tool.normalize_priority(priority)
        if due_date:
            try:
                date.fromisoformat(due_date)
            except ValueError:
                return f"Not logged: due_date {due_date!r} must be YYYY-MM-DD."

        google_task_id = None
        if deps.tasks_service is not None:
            try:
                existing = tasks_tool.find_open_task(deps.tasks_service, description)
                if existing:
                    return f"Already in My Tasks (not duplicated): {existing.get('title')}"
                google_task_id = tasks_tool.create_task(
                    deps.tasks_service, description, priority, due_date, priority_reason
                )
            except Exception as e:  # keep the run going; the local log still has it
                print(f"Warning: could not add task to Google Tasks: {e}")

        task_id = deps.task_log.log_task(description, due_date, priority, google_task_id, priority_reason)
        where = "added to My Tasks" if google_task_id else "logged locally"
        return f"Task {task_id} {where} ({priority} priority, due {due_date or 'no date'})."

    @tool
    def list_open_tasks() -> list[dict]:
        """List tasks you've previously logged that are still open."""
        return deps.task_log.list_open_tasks()

    @tool
    def mark_task_done(task_id: str) -> bool:
        """Mark a previously logged task as complete."""
        google_task_id = next(
            (t.get("google_task_id") for t in deps.task_log.list_open_tasks() if t["task_id"] == task_id), None
        )
        done = deps.task_log.mark_task_done(task_id)
        if done and google_task_id and deps.tasks_service is not None:
            try:
                tasks_tool.complete_task(deps.tasks_service, google_task_id)
            except Exception as e:
                print(f"Warning: could not complete task in Google Tasks: {e}")
        return done

    @tool
    def log_achievement(description: str) -> str:
        """Record, in one line, something that actually got accomplished —
        by you or evidenced in email. Call this as things get resolved, not
        only when asked for a summary."""
        return deps.task_log.log_achievement(description)

    @tool
    def list_recent_achievements(days: int = 1) -> list[dict]:
        """List achievements logged in the last `days` days. Use this to
        build an achievement summary."""
        return deps.task_log.list_recent_achievements(days)

    tools = [
        list_new_school_emails,
        mark_email_read,
        list_recent_school_emails,
        list_todays_calendar_events,
        check_calendar_conflict,
        propose_alternate_times,
        create_calendar_event,
        queue_email_for_approval,
        log_task,
        list_open_tasks,
        mark_task_done,
        log_achievement,
        list_recent_achievements,
    ]
    for t in tools:
        t.func = _report_errors(t.func)
    return tools
