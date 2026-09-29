"""
Verifies the single agent's TOOL LOOP end to end using a scripted chat model
in place of a real LLM. What this proves: the wiring is right — the real
tools actually execute, results flow back into the loop, boundaries like
"queue for approval, never send" hold structurally, and the loop terminates
on a final answer. What it deliberately does NOT prove: that a real model
will *choose* good tool sequences — that's a property of the live model and
the system prompt, and only running against real Claude with your real
inbox can show it. Scripted responses here play the role of "what a good
model would do."
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.build_agent import build_agent
from agent.deps import Deps
from approvals.approval_queue import ApprovalQueue
from tasks.task_log import TaskLog
from tests.fakes import FakeCalendarService, FakeToolCallMessage, ScriptedChatModel
from tools.demo_email import DemoEmail, InMemoryEmailStore

FIXED_NOW = datetime(2026, 9, 28, 8, 0, 0)


def make_deps(tmp_path, responses, existing_events=None, emails=None):
    model = ScriptedChatModel(responses=responses)
    calendar_service = FakeCalendarService(existing_events)
    approval_queue = ApprovalQueue(path=str(tmp_path / "approvals.json"))
    task_log = TaskLog(path=str(tmp_path / "task_log.json"))
    email_store = InMemoryEmailStore(emails or [])
    deps = Deps(
        mode="demo",
        model=model,
        calendar_service=calendar_service,
        calendar_id="primary",
        approval_queue=approval_queue,
        task_log=task_log,
        school_sender_allowlist=["ourschool.edu"],
        email_store=email_store,
        now=lambda: FIXED_NOW,
    )
    return deps, calendar_service, approval_queue, task_log


def tool_call(name: str, args: dict, call_id: str) -> dict:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def tool_names_called(result) -> list[str]:
    return [m.name for m in result["messages"] if m.type == "tool"]


def test_triage_queues_reply_for_approval_and_logs_achievement(tmp_path):
    emails = [
        DemoEmail(
            message_id="e1",
            sender="teacher.jsmith@ourschool.edu",
            subject="Field trip form",
            body="Can you return the permission slip by Friday?",
            received_at=FIXED_NOW,
            read=False,
        )
    ]
    responses = [
        FakeToolCallMessage.with_calls([tool_call("list_new_school_emails", {}, "c1")]),
        FakeToolCallMessage.with_calls(
            [
                tool_call(
                    "queue_email_for_approval",
                    {
                        "to": "teacher.jsmith@ourschool.edu",
                        "subject": "Re: Field trip form",
                        "body": "Thanks for the reminder — I'll return it by Friday.",
                    },
                    "c2",
                )
            ]
        ),
        FakeToolCallMessage.with_calls(
            [tool_call("log_achievement", {"description": "Drafted reply to Ms. Smith re: field trip form"}, "c3")]
        ),
        FakeToolCallMessage.final("Drafted a reply to Ms. Smith; it's waiting for your approval."),
    ]
    deps, _, approval_queue, task_log = make_deps(tmp_path, responses, emails=emails)
    agent = build_agent(deps)

    result = agent.invoke({"messages": [{"role": "user", "content": "triage"}]})

    assert tool_names_called(result) == ["list_new_school_emails", "queue_email_for_approval", "log_achievement"]
    pending = approval_queue.list_pending()
    assert len(pending) == 1
    only = next(iter(pending.values()))
    assert only["draft"]["to"] == "teacher.jsmith@ourschool.edu"
    assert len(task_log.list_recent_achievements(days=1)) == 1
    # No send tool exists at all — approve() was never called by the agent.
    assert all(v["status"] == "pending" for v in approval_queue._load().values())
    assert "waiting for your approval" in result["messages"][-1].content


def test_rundown_reads_calendar_and_email_then_summarizes(tmp_path):
    seeded_event = {
        "id": "seed-1",
        "summary": "Team meeting",
        "start": {"dateTime": "2026-09-28T09:00:00"},
        "end": {"dateTime": "2026-09-28T10:00:00"},
    }
    emails = [
        DemoEmail(
            message_id="e1",
            sender="frontdesk@ourschool.edu",
            subject="Doctor's note required",
            body="Please submit a doctor's note within 5 school days.",
            received_at=FIXED_NOW,
            read=False,
        )
    ]
    responses = [
        FakeToolCallMessage.with_calls([tool_call("list_todays_calendar_events", {}, "c1")]),
        FakeToolCallMessage.with_calls([tool_call("list_recent_school_emails", {"days": 1}, "c2")]),
        FakeToolCallMessage.final(
            "Today: Team meeting at 9am. Important email: front office needs a doctor's note within 5 school days."
        ),
    ]
    deps, _, _, _ = make_deps(tmp_path, responses, existing_events=[seeded_event], emails=emails)
    agent = build_agent(deps)

    result = agent.invoke({"messages": [{"role": "user", "content": "rundown"}]})

    assert tool_names_called(result) == ["list_todays_calendar_events", "list_recent_school_emails"]
    tool_outputs = {m.name: str(m.content) for m in result["messages"] if m.type == "tool"}
    # The real tools returned real data from the fakes, and it reached the loop.
    assert "Team meeting" in tool_outputs["list_todays_calendar_events"]
    assert "Doctor's note required" in tool_outputs["list_recent_school_emails"]
    assert "Team meeting" in result["messages"][-1].content


def test_achievements_reads_logged_items_then_summarizes(tmp_path):
    responses = [
        FakeToolCallMessage.with_calls([tool_call("list_recent_achievements", {"days": 1}, "c1")]),
        FakeToolCallMessage.final("Today: replied to field trip form, scheduled science fair."),
    ]
    deps, _, _, task_log = make_deps(tmp_path, responses)
    task_log.log_achievement("Replied to field trip form")
    task_log.log_achievement("Scheduled science fair")
    agent = build_agent(deps)

    result = agent.invoke({"messages": [{"role": "user", "content": "achievements"}]})

    assert tool_names_called(result) == ["list_recent_achievements"]
    tool_output = next(str(m.content) for m in result["messages"] if m.type == "tool")
    assert "Replied to field trip form" in tool_output
    assert "Scheduled science fair" in tool_output


def test_calendar_conflict_leads_to_autonomous_alternate_not_double_booking(tmp_path):
    conflicting_event = {
        "id": "seed-1",
        "summary": "Standing meeting",
        "start": {"dateTime": "2026-09-29T09:00:00"},
        "end": {"dateTime": "2026-09-29T10:00:00"},
    }
    responses = [
        FakeToolCallMessage.with_calls(
            [tool_call("check_calendar_conflict", {"start_iso": "2026-09-29T09:00:00", "end_iso": "2026-09-29T10:00:00"}, "c1")]
        ),
        FakeToolCallMessage.with_calls(
            [tool_call("propose_alternate_times", {"desired_start_iso": "2026-09-29T09:00:00", "duration_minutes": 60}, "c2")]
        ),
        FakeToolCallMessage.with_calls(
            [
                tool_call(
                    "create_calendar_event",
                    {
                        "title": "Science Fair",
                        "start_iso": "2026-09-29T10:00:00",
                        "end_iso": "2026-09-29T11:00:00",
                        "description": "Original 9am slot conflicted with a standing meeting.",
                    },
                    "c3",
                )
            ]
        ),
        FakeToolCallMessage.final("Scheduled Science Fair at 10am instead of 9am because 9am was taken."),
    ]
    deps, calendar_service, _, _ = make_deps(tmp_path, responses, existing_events=[conflicting_event])
    agent = build_agent(deps)

    result = agent.invoke({"messages": [{"role": "user", "content": "schedule the science fair at 9am on the 29th"}]})

    assert tool_names_called(result) == ["check_calendar_conflict", "propose_alternate_times", "create_calendar_event"]
    # The REAL alternates tool ran against the real conflict and produced 10am
    # as a free slot — the scripted create call matches what it actually found.
    alternates_output = next(str(m.content) for m in result["messages"] if m.type == "tool" and m.name == "propose_alternate_times")
    assert "2026-09-29T10:00:00" in alternates_output
    assert "2026-09-29T09:00:00" not in alternates_output
    assert len(calendar_service._events.created) == 1
    assert calendar_service._events.created[0]["start"]["dateTime"] == "2026-09-29T10:00:00"
