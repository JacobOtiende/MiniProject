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

from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Optional

from langchain_core.tools import tool

from tools import calendar_tool, gmail_tool


def _serialize(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        d = asdict(obj)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d
    return obj


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
            return [_serialize(e) for e in deps.email_store.fetch_new()]
        emails = gmail_tool.fetch_new_school_emails(deps.gmail_service, deps.school_sender_allowlist)
        return [_serialize(e) for e in emails]

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
    def log_task(description: str, due_date: Optional[str] = None) -> str:
        """Log something that needs follow-through but isn't resolved yet,
        so it's remembered on your next run instead of silently dropped."""
        return deps.task_log.log_task(description, due_date)

    @tool
    def list_open_tasks() -> list[dict]:
        """List tasks you've previously logged that are still open."""
        return deps.task_log.list_open_tasks()

    @tool
    def mark_task_done(task_id: str) -> bool:
        """Mark a previously logged task as complete."""
        return deps.task_log.mark_task_done(task_id)

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

    return [
        list_new_school_emails,
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
