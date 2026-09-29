"""
Real Gmail API calls for the School Agent's trigger source.

This is polling, not a push webhook: main.py calls fetch_new_school_emails()
on the Control Tower's wake interval (default 4h, config.py). See
README.md > "Why polling, not push" for why that's the right tradeoff here
instead of Gmail's Pub/Sub push notifications.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass
class SchoolEmail:
    message_id: str
    sender: str
    subject: str
    body: str
    received_at: str  # RFC 2822 date header, as Gmail returns it


def _build_query(allowlist: list[str], unread_only: bool = True, since_iso: str | None = None) -> str:
    if not allowlist:
        raise ValueError(
            "SCHOOL_SENDER_ALLOWLIST is empty — the agent needs at least one "
            "sender domain/address to treat as school correspondence."
        )
    senders = " OR ".join(f"from:{s}" for s in allowlist)
    query = f"({senders})"
    if unread_only:
        query += " is:unread"
    if since_iso:
        # Gmail's search operator wants YYYY/MM/DD, not full ISO 8601.
        date_part = since_iso.split("T")[0].replace("-", "/")
        query += f" after:{date_part}"
    return query


def _extract_body(payload: dict) -> str:
    """Walk a Gmail message payload and return the best plain-text body
    we can find, decoding the base64url Gmail uses."""

    def decode(data: str) -> str:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")

    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return decode(payload["body"]["data"])

    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return decode(part["body"]["data"])
    # Fall back to the first part with any data at all (e.g. text/html only).
    for part in payload.get("parts", []) or []:
        if part.get("body", {}).get("data"):
            return decode(part["body"]["data"])
    return ""


def _fetch(gmail_service, query: str, max_results: int) -> list[SchoolEmail]:
    response = (
        gmail_service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    message_stubs = response.get("messages", [])

    emails: list[SchoolEmail] = []
    for stub in message_stubs:
        full = (
            gmail_service.users()
            .messages()
            .get(userId="me", id=stub["id"], format="full")
            .execute()
        )
        headers = {h["name"].lower(): h["value"] for h in full["payload"].get("headers", [])}
        emails.append(
            SchoolEmail(
                message_id=full["id"],
                sender=headers.get("from", "unknown"),
                subject=headers.get("subject", "(no subject)"),
                body=_extract_body(full["payload"]),
                received_at=headers.get("date", ""),
            )
        )
    return emails


def fetch_new_school_emails(gmail_service, allowlist: list[str], max_results: int = 25) -> list[SchoolEmail]:
    """Real, live call against the Gmail API — lists UNREAD messages from
    the school sender allowlist. This is the triage trigger source."""
    return _fetch(gmail_service, _build_query(allowlist, unread_only=True), max_results)


def fetch_recent_school_emails(gmail_service, allowlist: list[str], since_iso: str, max_results: int = 50) -> list[SchoolEmail]:
    """Real, live call against the Gmail API — lists ALL school-allowlisted
    messages (read or unread) since since_iso. Used for the daily rundown
    and achievement summary, where the agent needs the day's full picture,
    not just what hasn't been opened yet."""
    return _fetch(gmail_service, _build_query(allowlist, unread_only=False, since_iso=since_iso), max_results)


def create_draft(gmail_service, to: str, subject: str, body: str) -> str:
    """Create a draft email in Gmail. Returns the draft's message ID."""
    from email.mime.text import MIMEText

    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = {'message': {'raw': raw}}

    result = gmail_service.users().drafts().create(userId='me', body=draft).execute()
    return result['id']
