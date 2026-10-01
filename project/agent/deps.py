"""
Everything the single agent's tools need, injected once at build time —
same dependency-injection shape as the old graph/build_graph.py's Deps,
kept because it's what makes the tools testable with fakes instead of
live services.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


@dataclass
class Deps:
    mode: str  # "demo" or "live"
    model: Any  # a LangChain BaseChatModel (ChatOpenAI in real use; a fake in tests)
    calendar_service: Any
    calendar_id: str
    approval_queue: Any  # approvals.approval_queue.ApprovalQueue
    task_log: Any  # tasks.task_log.TaskLog
    school_sender_allowlist: list[str] = field(default_factory=list)
    gmail_service: Any = None  # required when mode == "live"
    email_store: Any = None  # required when mode == "demo" (tools.demo_email.InMemoryEmailStore)
    tasks_service: Any = None  # Google Tasks ("My Tasks"); None skips syncing
    # Unread school emails handed to the agent this run, and which of those
    # are now marked read — see agent.tools.mark_remaining_emails_read.
    seen_email_ids: set[str] = field(default_factory=set)
    read_email_ids: set[str] = field(default_factory=set)
    now: Callable[[], datetime] = field(default_factory=lambda: datetime.now)
    logger: Any = None  # observability.logging.RunLogger for tracing tool calls
