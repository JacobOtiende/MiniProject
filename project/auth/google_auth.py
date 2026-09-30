"""
Real OAuth against the user's own Google account — no mocked tokens.

The first time this runs it opens a browser consent screen (standard
InstalledAppFlow behavior); every run after that reuses the cached token in
GOOGLE_OAUTH_TOKEN_PATH and refreshes it silently. This is the same pattern
Google's own quickstart samples use for a personal/desktop project, and it's
the right amount of infrastructure for a course project — a production
Gmail push-notification webhook needs a public HTTPS endpoint and a verified
domain, which is out of scope here (see README "Why polling, not push").
"""
from __future__ import annotations

import os

import google_auth_httplib2
import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest

# Gmail: read emails and create drafts (send via Gmail, not directly)
# plus full Calendar access (create/update/query events) and Google Tasks
# (write follow-ups into "My Tasks").
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]


def get_credentials(client_secrets_path: str, token_path: str) -> Credentials:
    """Return valid user credentials, running the OAuth consent flow
    only if no cached/refreshable token exists yet. Uses Firefox for auth."""
    import webbrowser

    creds: Credentials | None = None

    if os.path.exists(token_path):
        # Load with the scopes the token was actually granted (passing SCOPES
        # here would overwrite them). A token cached before a scope was added
        # still looks valid; force a fresh consent instead of failing later
        # with "Insufficient Permission".
        creds = Credentials.from_authorized_user_file(token_path)
        if not creds.has_scopes(SCOPES):
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_path):
                raise FileNotFoundError(
                    f"Google OAuth client secrets not found at {client_secrets_path!r}. "
                    "Download it from Google Cloud Console > APIs & Services > "
                    "Credentials > OAuth client ID (Desktop app) and point "
                    "GOOGLE_OAUTH_CLIENT_SECRETS at it. See README.md."
                )
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            # Register Firefox and use it for OAuth browser
            webbrowser.register('firefox', None, webbrowser.BackgroundBrowser('C:\\Program Files\\Mozilla Firefox\\firefox.exe'))
            creds = flow.run_local_server(port=0, browser='firefox')

        os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def _build_service(api: str, version: str, client_secrets_path: str, token_path: str):
    """Build a thread-safe API client. The agent runs parallel tool calls on
    worker threads, and httplib2.Http is not thread-safe: sharing one
    connection corrupts the TLS stream (ssl.SSLError WRONG_VERSION_NUMBER).
    Google's documented fix is a fresh Http per request via requestBuilder."""
    creds = get_credentials(client_secrets_path, token_path)

    def build_request(_http, *args, **kwargs):
        return HttpRequest(google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http()), *args, **kwargs)

    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http())
    return build(api, version, http=authorized_http, requestBuilder=build_request)


def build_gmail_service(client_secrets_path: str, token_path: str):
    return _build_service("gmail", "v1", client_secrets_path, token_path)


def build_calendar_service(client_secrets_path: str, token_path: str):
    return _build_service("calendar", "v3", client_secrets_path, token_path)


def build_tasks_service(client_secrets_path: str, token_path: str):
    return _build_service("tasks", "v1", client_secrets_path, token_path)
