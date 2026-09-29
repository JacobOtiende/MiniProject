from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.gmail_tool import _build_query, _extract_body


def test_query_includes_every_allowlisted_sender_and_unread_by_default():
    query = _build_query(["schoolapp.example.com", "frontdesk@ourschool.edu"])
    assert "from:schoolapp.example.com" in query
    assert "from:frontdesk@ourschool.edu" in query
    assert "is:unread" in query


def test_query_for_recent_drops_unread_filter_and_adds_date():
    query = _build_query(["ourschool.edu"], unread_only=False, since_iso="2026-09-27T08:00:00")
    assert "is:unread" not in query
    assert "after:2026/09/27" in query


def test_empty_allowlist_fails_loudly_instead_of_polling_whole_inbox():
    with pytest.raises(ValueError):
        _build_query([])


def test_extract_body_decodes_gmail_base64url_plain_text():
    encoded = base64.urlsafe_b64encode(b"Hello from school").decode()
    payload = {"mimeType": "multipart/alternative", "parts": [{"mimeType": "text/plain", "body": {"data": encoded}}]}
    assert _extract_body(payload) == "Hello from school"
