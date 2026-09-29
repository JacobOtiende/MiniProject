"""
In-memory email store for CHILDOPS_MODE=demo, mirroring demo_calendar.py's
role: same call shape the agent's tools expect, no live Gmail needed. Seeded
from data/sample_emails.json with fabricated timestamps and read-flags so
both "what's new" (triage) and "what happened recently" (rundown,
achievements) queries have something realistic to return.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

SAMPLE_EMAILS_PATH = Path(__file__).parent.parent / "data" / "sample_emails.json"


@dataclass
class DemoEmail:
    message_id: str
    sender: str
    subject: str
    body: str
    received_at: datetime
    read: bool


class InMemoryEmailStore:
    def __init__(self, emails: list[DemoEmail]):
        self._emails = emails

    def fetch_new(self) -> list[DemoEmail]:
        return [e for e in self._emails if not e.read]

    def fetch_recent(self, since: datetime) -> list[DemoEmail]:
        return [e for e in self._emails if e.received_at >= since]

    def mark_read(self, message_id: str) -> None:
        for e in self._emails:
            if e.message_id == message_id:
                e.read = True


def default_seed_emails(today: datetime) -> InMemoryEmailStore:
    with open(SAMPLE_EMAILS_PATH) as f:
        raw = json.load(f)

    emails: list[DemoEmail] = []
    for i, item in enumerate(raw):
        # Spread them across today and yesterday; mark the oldest as already
        # read (simulating something the parent already saw and handled) so
        # the achievement/rundown split between "new" and "recent" is real.
        received_at = today - timedelta(hours=3 * i)
        emails.append(
            DemoEmail(
                message_id=f"demo-{i+1}",
                sender=item["sender"],
                subject=item["subject"],
                body=item["body"],
                received_at=received_at,
                read=(i == len(raw) - 1),  # the oldest sample is "already read"
            )
        )
    return InMemoryEmailStore(emails)
