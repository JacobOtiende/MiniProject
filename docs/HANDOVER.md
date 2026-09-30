# MiniProject — Unified School Operations Agent

*Last updated: 2026-09-29*

## Current Status

**MiniProject** is a single-agent school operations assistant (harmonized from ChildOps and SingleAgentOps). One command, `python main.py`, runs the whole daily cycle: triage new school email (calendar events, Google Tasks, reply drafts), write a start-of-day briefing and an end-of-day wrap-up (saved as two daily summary tasks), mark handled email read, and walk through drafts awaiting approval.

**Health:** 24/24 tests pass. Live mode runs against real Gmail and Calendar. Google Tasks is built and tested with fakes but blocked live (API not enabled). GitHub: https://github.com/JacobOtiende/MiniProject

---

## Completed

- ✅ Single-agent architecture (13 tools), system prompt with hard boundaries
- ✅ Single command: `python main.py` → triage → rundown (☀️ Start of day) → wrap-up (🌙 End of day) → one review pass
- ✅ Gmail: triage, replies saved as Gmail drafts, handled email marked read (agent tool + after-triage sweep)
- ✅ Calendar: conflict check, alternates, event creation; timezone offsets fixed
- ✅ Google Tasks: agent-chosen priority labels (🔴 [HIGH] / 🟠 [MEDIUM] / 🟢 [LOW]) with reasons, due dates, due-date order, de-duplication, completion sync, catch-up sync
- ✅ Daily summary tasks in a separate "MyAgent Daily Summary" list, updated in place
- ✅ Reliability: thread-safe Google clients, locked/atomic data files, tool errors reported to the model instead of crashing
- ✅ OAuth auto re-consent when a scope is added (`gmail.readonly`, `gmail.modify`, `calendar`, `tasks`)
- ✅ `data/task_log.json` untracked from git

---

## In Progress

- 🔄 Live validation of Google Tasks (blocked, see below)

---

## Not Started

- ⚪ Scheduled runs (Task Scheduler) — e.g. morning and evening, so the two summaries are fresh
- ⚪ Rate-limit backoff/retry for OpenAI calls
- ⚪ Approve/reject in the review loop does not yet send or delete the matching Gmail draft
- ⚪ Removing `data/task_log.json` from public git history (needs a history rewrite + force push; user decision)

---

## Blockers

- 🟠 **Google Tasks API disabled** for Google Cloud project `768142962405` (the OAuth client's project). All Tasks calls return `403 accessNotConfigured`. Tasks are kept locally and sync on the first run after it is enabled.

---

## Important Decisions

1. **Single-agent over multi-agent.** No second-opinion agent; mitigated by the hard boundary that no send tool exists.
2. **Policy as instruction, not enforcement.** Behavior lives in `agent/system_prompt.py`; live runs are the evaluation.
3. **Priority is the agent's judgment**, shown as a title label because Google Tasks has no color, font, or priority field; the reason goes in the notes.
4. **Every triaged email is marked read** (user request). Failures are logged as tasks rather than left unread for retry.
5. **Daily summaries are separate** from the task log and from My Tasks.
6. **Scripted tests** prove tool flow, not model judgment.

---

## Known Issues

- The agent is signed in as **childops2@gmail.com**; tasks only appear in that account's Google Tasks.
- 7 unread school emails remained after the last live run; the next run will process them once (duplicates of earlier events are possible that one time).
- Google OAuth tokens expire every 7 days in Testing mode; the next run re-prompts.
- Older commits contain `data/task_log.json` with real school details (public repo).
- The model sometimes skips `mark_email_read`; the after-triage sweep covers it.

---

## Immediate Next Action

Enable the **Google Tasks API** at https://console.developers.google.com/apis/api/tasks.googleapis.com/overview?project=768142962405 (confirm the project selector shows 768142962405), wait 2–3 minutes, then run `python main.py` in `MiniProject/project/`. Verify, signed in to tasks.google.com as childops2@gmail.com, that: (1) tasks appear in My Tasks in due-date order with priority labels and dates, (2) the "MyAgent Daily Summary" list has ☀️ Start of day and 🌙 End of day, (3) the school emails show as read in Gmail. Record results in `docs/DAILY_LOG.md`.

---

## Recommended Next Steps

1. Review the agent's priority choices and reasons on real email; tune the prompt if it misjudges.
2. Schedule two runs a day with Windows Task Scheduler (morning for Start of day, evening for End of day).
3. Wire approve/reject in the review loop to send or delete the Gmail draft.
4. Decide whether to purge `data/task_log.json` from git history.

---

## Important Context

- **Run:** `cd MiniProject/project && python main.py` (`.env` has `MYAGENT_MODE=live`; set `demo` for fake Google services).
- **Data:** `data/task_log.json` (local tasks + achievements, git-ignored), `data/pending_approvals.json` (draft queue, git-ignored). A corrupt file is moved aside as `*.corrupt-<time>`.
- **Safety:** there is no send tool; drafts need human approval.
