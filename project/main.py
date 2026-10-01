"""
Entry point for MyAgent — single-agent school operations assistant.

    python main.py

One command runs the whole cycle, in order:
  1. triage        — check new school email and act on it (events, tasks, drafts)
  2. rundown       — today's calendar + email briefing
  3. achievements  — what got accomplished recently
  4. review        — walk through every email draft awaiting your approval

MYAGENT_MODE=demo (default) makes real OpenAI calls but fakes the
Google side (in-memory calendar + seeded sample emails) so you can run the
whole cycle without Google OAuth. MYAGENT_MODE=live polls your real Gmail
and writes to your real Calendar.
"""
from __future__ import annotations

import sys
from datetime import datetime

from langchain_openai import ChatOpenAI

from agent.build_agent import build_agent
from agent.deps import Deps
from agent.tools import mark_remaining_emails_read, sync_unsynced_tasks
from approvals.approval_queue import ApprovalQueue, run_red_alert_loop
from auth.google_auth import build_calendar_service, build_gmail_service, build_tasks_service
from config import load_settings
from observability.logging import RunLogger
from tasks.task_log import TaskLog
from tools.demo_calendar import InMemoryCalendarService, default_seed_events
from tools.demo_email import default_seed_emails
from tools import tasks_tool
from tools.demo_tasks import InMemoryTasksService

# Track current phase for token logging
_current_phase = None

# Run in this order: triage first so the rundown and achievements summary
# reflect whatever it just created, logged, or drafted.
PHASE_INSTRUCTIONS = {
    "triage": (
        "Check for new school emails and handle each one using your tools and "
        "judgment, within your policy boundaries. If there's nothing new, say so."
    ),
    "rundown": (
        "Produce today's START-OF-DAY briefing: check today's calendar events, "
        "your open tasks, and recent school emails (last 1-2 days). Cover what's "
        "on the calendar today, tasks that are overdue or due today, and the "
        "high-priority tasks coming up next, soonest first. It is saved as the "
        "parent's 'Start of day' summary task, so write plain text with simple "
        "dash bullets — no markdown headings, bold, or tables."
    ),
    "achievements": (
        "Produce today's END-OF-DAY wrap-up: review achievements logged today "
        "and your open tasks. Cover what got done today, what is still open "
        "(highest priority first), and what is due tomorrow. It is saved as the "
        "parent's 'End of day' summary task, so write plain text with simple "
        "dash bullets — no markdown headings, bold, or tables."
    ),
}

# Phases whose written output becomes a daily summary task in Google Tasks.
SUMMARY_TASK_FOR_PHASE = {"rundown": "start", "achievements": "end"}


def build_deps(settings, logger=None) -> Deps:
    model = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
    task_log = TaskLog(path="./data/task_log.json")

    if settings.mode == "demo":
        now = datetime.now()
        approval_queue = ApprovalQueue(path="./data/pending_approvals.json", gmail_service=None)
        return Deps(
            mode="demo",
            model=model,
            calendar_service=InMemoryCalendarService(seed_events=default_seed_events(now)),
            calendar_id="primary",
            approval_queue=approval_queue,
            task_log=task_log,
            school_sender_allowlist=settings.school_sender_allowlist or ["ourschool.edu"],
            email_store=default_seed_emails(now),
            tasks_service=InMemoryTasksService(),
            logger=logger,
        )

    gmail_service = build_gmail_service(settings.google_oauth_client_secrets, settings.google_oauth_token_path)
    calendar_service = build_calendar_service(settings.google_oauth_client_secrets, settings.google_oauth_token_path)
    approval_queue = ApprovalQueue(path="./data/pending_approvals.json", gmail_service=gmail_service)
    return Deps(
        mode="live",
        model=model,
        calendar_service=calendar_service,
        calendar_id=settings.target_calendar_id,
        approval_queue=approval_queue,
        task_log=task_log,
        school_sender_allowlist=settings.school_sender_allowlist,
        gmail_service=gmail_service,
        tasks_service=build_tasks_service(settings.google_oauth_client_secrets, settings.google_oauth_token_path),
        logger=logger,
    )


def _google_tasks_step(what: str, tasks_service, action) -> None:
    """Google Tasks extras shouldn't abort the run if the API is unavailable."""
    if tasks_service is None:
        return
    try:
        action()
    except Exception as e:
        print(f"Warning: could not {what}: {e}")


def main() -> None:
    # Agent replies can include the priority markers (🔴🟠🟢); don't let a
    # legacy Windows console codepage crash the run on them.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Initialize observability
    logger = RunLogger()
    logger.logger.info(f"Starting MyAgent run: {logger.run_id}")

    settings = load_settings()
    deps = build_deps(settings, logger=logger)

    # Wrap model to track token usage
    original_invoke = deps.model.invoke
    def invoke_with_tracking(input_obj, **kwargs):
        result = original_invoke(input_obj, **kwargs)
        # Extract token usage from response metadata
        if hasattr(result, 'response_metadata') and result.response_metadata:
            usage = result.response_metadata.get('usage', {})
            if usage and hasattr(logger, 'record_tokens'):
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                if input_tokens or output_tokens:
                    logger.record_tokens(_current_phase, input_tokens, output_tokens)
        return result
    deps.model.invoke = invoke_with_tracking

    agent = build_agent(deps)

    # Global variable to track current phase for token tracking
    global _current_phase

    for phase, instruction in PHASE_INSTRUCTIONS.items():
        _current_phase = phase
        logger.record_phase_start(phase)

        result = agent.invoke(
            {"messages": [{"role": "user", "content": instruction}]}
        )

        print(f"\n=== MyAgent [{phase}] ===\n")
        print(result["messages"][-1].content)

        logger.record_phase_end(phase)

        if phase == "triage":
            swept = mark_remaining_emails_read(deps)
            print(f"\n{len(deps.seen_email_ids)} school email(s) triaged and marked read in Gmail"
                  + (f" ({swept} the agent hadn't marked itself)." if swept else "."))
            _google_tasks_step("sync tasks to My Tasks", deps.tasks_service, lambda: sync_unsynced_tasks(deps))
        if phase in SUMMARY_TASK_FOR_PHASE:
            kind = SUMMARY_TASK_FOR_PHASE[phase]
            summary = result["messages"][-1].content
            _google_tasks_step(
                f"update the {tasks_tool.SUMMARY_KINDS[kind]} summary task",
                deps.tasks_service,
                lambda: tasks_tool.upsert_daily_summary(deps.tasks_service, kind, summary, deps.now().date()),
            )

    print("\n=== MyAgent [review] ===")
    logger.record_phase_start("review")
    # One pass per run: anything left for "Later" stays pending and
    # alerts again on the next run.
    run_red_alert_loop(deps.approval_queue, max_polls=1)
    logger.record_phase_end("review")

    # Save all logs and metrics
    summary = logger.finalize()
    print(f"\n=== Observability Summary ===")
    print(f"Logs saved to: {summary['metrics_file']}")
    print(f"Tool calls: {summary['tool_summary']['total_calls']} "
          f"({summary['tool_summary']['success_rate']:.1%} success)")
    print(f"Total tokens: {summary['token_summary']['total_tokens']} "
          f"(${summary['token_summary']['total_cost_usd']:.4f})")


if __name__ == "__main__":
    main()
