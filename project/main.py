"""
Entry point for the single-agent ChildOps build.

    python main.py triage                # check new school email, act on it
    python main.py rundown                # today's calendar + email briefing
    python main.py achievements           # what got accomplished recently
    python main.py rundown --review       # then open the approval review loop

CHILDOPS_MODE=demo (default) makes real OpenAI calls but fakes the
Google side (in-memory calendar + seeded sample emails) so you can run all
three modes without Google OAuth. CHILDOPS_MODE=live polls your real Gmail
and writes to your real Calendar.
"""
from __future__ import annotations

import argparse
from datetime import datetime

from langchain_openai import ChatOpenAI

from agent.build_agent import build_agent
from agent.deps import Deps
from approvals.approval_queue import ApprovalQueue, run_red_alert_loop
from auth.google_auth import build_calendar_service, build_gmail_service
from config import load_settings
from tasks.task_log import TaskLog
from tools.demo_calendar import InMemoryCalendarService, default_seed_events
from tools.demo_email import default_seed_emails

MODE_INSTRUCTIONS = {
    "triage": (
        "Check for new school emails and handle each one using your tools and "
        "judgment, within your policy boundaries. If there's nothing new, say so."
    ),
    "rundown": (
        "Produce today's rundown: check today's calendar events and recent "
        "school emails (last 1-2 days), then write a short, clear daily briefing "
        "covering what's on the calendar today and anything important from email."
    ),
    "achievements": (
        "Review your task log and recently logged achievements to determine what "
        "has actually gotten accomplished recently. Write a concise achievement "
        "summary a parent could skim in a few seconds."
    ),
}


def build_deps(settings, args) -> Deps:
    model = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
    approval_queue = ApprovalQueue(path="./data/pending_approvals.json")
    task_log = TaskLog(path="./data/task_log.json")

    if settings.mode == "demo":
        now = datetime.now()
        return Deps(
            mode="demo",
            model=model,
            calendar_service=InMemoryCalendarService(seed_events=default_seed_events(now)),
            calendar_id="primary",
            approval_queue=approval_queue,
            task_log=task_log,
            school_sender_allowlist=settings.school_sender_allowlist or ["ourschool.edu"],
            email_store=default_seed_emails(now),
        )

    gmail_service = build_gmail_service(settings.google_oauth_client_secrets, settings.google_oauth_token_path)
    calendar_service = build_calendar_service(settings.google_oauth_client_secrets, settings.google_oauth_token_path)
    return Deps(
        mode="live",
        model=model,
        calendar_service=calendar_service,
        calendar_id=settings.target_calendar_id,
        approval_queue=approval_queue,
        task_log=task_log,
        school_sender_allowlist=settings.school_sender_allowlist,
        gmail_service=gmail_service,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_mode", choices=["triage", "rundown", "achievements"])
    parser.add_argument("--review", action="store_true", help="Open the pending-approval review loop after running.")
    args = parser.parse_args()

    settings = load_settings()
    deps = build_deps(settings, args)
    agent = build_agent(deps)

    result = agent.invoke({"messages": [{"role": "user", "content": MODE_INSTRUCTIONS[args.run_mode]}]})
    final_message = result["messages"][-1]
    print(f"\n=== ChildOps agent [{args.run_mode}] ===\n")
    print(final_message.content)

    if args.review:
        run_red_alert_loop(deps.approval_queue)
    elif deps.approval_queue.list_pending():
        print(f"\n{len(deps.approval_queue.list_pending())} email draft(s) pending your review. Run with --review to see them.")


if __name__ == "__main__":
    main()
