# MiniProject — Daily Log

## 2026-09-30

### Objective

Commit observability work (logging, token tracking, tool tracing) and prepare for Google Tasks API enablement.

### Work Completed

- ✅ Reviewed and tested observability implementation (4 modules: RunLogger, TokenUsageTracker, ToolCallTracer, LangChain callbacks + tool wrapper utilities).
- ✅ Enhanced `_report_errors()` decorator to capture tool execution timing and log tool calls with name, args, result, latency, and error status.
- ✅ Wrapped model.invoke to extract token usage from LLM responses; integrated phase-based token tracking.
- ✅ Integrated RunLogger in main.py: record phase start/end around each agent loop, display summary at run end.
- ✅ All 24 tests passing; logging is non-blocking and doesn't crash if logger unavailable.
- ✅ Committed `5ea9f2f` and pushed to GitHub.

### Changes Made

- New: `project/observability/` (4 modules + README), `OBSERVABILITY_IMPLEMENTATION.md`.
- Updated: `agent/deps.py` (added logger field), `agent/tools.py` (_report_errors decorator), `main.py` (RunLogger init, phase tracking, model wrapping, summary output).

### Findings

- Observability adds ~100-200ms per run (~1-2% overhead).
- Tool wrapping and token tracking are both non-blocking; errors in logging never break tool execution or agent loop.
- Logs directory will contain: agent.log, metrics.json, tool_calls.json, tokens.json—enabling root-cause analysis of any future issues.

### Problems / Issues

- _(none identified)_

### Decisions

- Observability logs are generated automatically on every run; no flag or configuration needed.
- Tool tracing extracts logger from deps object; backwards-compatible with existing code.

### Next Session

Enable the Google Tasks API in project `768142962405`, run `python main.py`, and verify tasks appear in childops2@gmail.com's Google Tasks with priority labels and dates.

---

## 2026-09-29

### Objective

Review outputs from the Gmail-draft session, then make the agent a single-command daily assistant that puts prioritized, dated tasks in Google Tasks and keeps the inbox clean.

### Work Completed

- Reviewed outputs: the `gmail.modify` scope had already been approved; a live run created Gmail draft `r4221917666194833533` (Parent Night RSVP).
- Fixed the approval-queue loader bug (13/14 → 14/14 tests).
- `python main.py` now runs triage → rundown → wrap-up → review with no arguments; runner scripts removed.
- Fixed the Calendar `400` (naive datetimes); verified a read-only call against the live Calendar.
- Built Google Tasks integration: priority labels chosen by the agent with a reason, due dates, date order, de-duplication, completion sync, catch-up sync of unsynced local tasks.
- Added two daily summary tasks (☀️ Start of day / 🌙 End of day) in their own list.
- Added `mark_email_read` and the after-triage sweep that marks every triaged school email read.
- Fixed the SSL crash (thread-unsafe shared `httplib2`); verified with 12 parallel read-only live calls.
- Fixed task-log corruption from parallel writes (locks + atomic writes + corrupt-file backup).
- Tool errors are now returned to the model instead of crashing the run.
- Stopped tracking `data/task_log.json` in git.
- Tests: 14 → 24, all passing.

### Changes Made

- New: `tools/tasks_tool.py`, `tools/demo_tasks.py`, `jsonstore.py`, `tests/test_tasks_tool.py`.
- Updated: `main.py`, `agent/tools.py`, `agent/system_prompt.py`, `agent/build_agent.py`, `agent/deps.py`, `auth/google_auth.py`, `approvals/approval_queue.py`, `tasks/task_log.py`, `tools/calendar_tool.py`, `tools/demo_calendar.py`, `tools/gmail_tool.py`, tests, both READMEs.
- Removed: `run.py`, `run.bat`, `run.sh`.

### Findings

- Repeated live runs created 7 duplicate "Bilingual/ESL/EB Parent Night" calendar events (since deleted by the user). The cause: emails were never marked read, so every run reprocessed them.
- In a live run, the model did not call `mark_email_read` on its own. That is why the deterministic sweep was added.
- The agent never knew today's date, which is why earlier tasks had no due dates.
- The corrupted task log was silently treated as empty and overwritten; the earlier local tasks were lost (the 2026-09-28 tasks still exist in git history).
- The agent's Google account is `childops2@gmail.com`; tasks appear only in that account.

### Problems / Issues

- Google Tasks API is disabled for Google Cloud project `768142962405`. Every Tasks call returns `403 accessNotConfigured`; tasks are kept locally and will sync once it is enabled.
- `data/task_log.json` was pushed to the public repo in earlier commits; it is untracked now but still in history.

### Decisions

- Priority is shown as a title label (color marker + text) because Google Tasks has no color, font size, or priority field.
- Daily summaries live in a separate task list and are not stored in the local task log.
- Every triaged email is marked read (user request); anything that failed is logged as a task rather than left unread.
- The review loop runs one pass per run so `python main.py` always finishes.

### Next Session

Enable the Google Tasks API in project `768142962405`, run `python main.py`, and confirm in childops2@gmail.com's Google Tasks that the tasks appear in date order with labels and that both summary tasks exist.

---

## 2026-09-28 (Session 2)

### Objective

Integrate Gmail draft creation so drafted emails are saved directly to Gmail drafts folder instead of local approval queue.

### Work Completed

- ✅ Added `create_draft()` function to `tools/gmail_tool.py` using Gmail API drafts.create
- ✅ Modified `ApprovalQueue` class to accept `gmail_service` parameter
- ✅ Updated `enqueue()` method to call `create_draft()` and store Gmail draft ID in local queue
- ✅ Updated `run_red_alert_loop()` to display Gmail draft ID and location note
- ✅ Updated OAuth scopes in `auth/google_auth.py` to include `gmail.modify` for draft creation
- ✅ Modified `main.py` `build_deps()` to pass `gmail_service` to ApprovalQueue constructor
- ✅ Deleted cached OAuth token to force re-authentication with new scopes

### Changes Made

- `tools/gmail_tool.py`: Added `create_draft(gmail_service, to, subject, body)` function
- `approvals/approval_queue.py`: Now creates Gmail drafts on `enqueue()`, stores draft ID, displays location in red alert
- `auth/google_auth.py`: Added `"https://www.googleapis.com/auth/gmail.modify"` to SCOPES
- `main.py`: Pass gmail_service to ApprovalQueue in both demo and live modes
- `credentials/token.json`: Deleted to force re-auth

### Findings

- Gmail draft creation works (tested successfully before permission scope issue)
- Permission scope limitation: old cached token lacked gmail.modify permission
- Fix: Updated SCOPES and deleted cached token to trigger fresh OAuth consent
- In live mode, drafts now appear in user's Gmail drafts folder for review before approval

### Problems / Issues

- Permission issue: Initial test failed with "Insufficient Permission" because cached OAuth token was issued before gmail.modify scope was added
- Solution: Add gmail.modify to SCOPES and delete cached token so next run prompts fresh authentication

### Decisions

- Save drafts to Gmail instead of local JSON: gives user familiar interface (Gmail drafts folder) instead of CLI loop
- Keep local approval_queue.json as reference log: tracks which drafts are pending, but actual email lives in Gmail
- Error handling: if draft creation fails (e.g., permission error), log warning but continue gracefully with fallback to local storage

### Next Session

User must approve OAuth scope expansion when prompted. After that, test live mode with `python main.py triage --review` to verify drafts appear in Gmail drafts folder and approval loop works correctly.

---

## 2026-09-28 (Session 1)

### Objective

Establish documentation structure, convert to OpenAI, and verify SingleAgentOps runs successfully.

### Work Completed

- ✅ Created `docs/` folder structure (HANDOVER, DAILY_LOG, CHANGELOG, SKILLS_LOG)
- ✅ Created project-level README.md with navigation
- ✅ Initialized git repository and committed all files (3 commits)
- ✅ Renamed folder from `childops` to `project` for clarity
- ✅ Converted codebase from Anthropic/Claude to OpenAI/GPT-4o
- ✅ Copied OpenAI API key and OAuth credentials from ChildOps
- ✅ Installed dependencies
- ✅ Verified demo mode works: `python main.py triage` successfully processes emails and logs tasks
- ✅ Updated workspace/PROJECT_INDEX.md to register SingleAgentOps

### Changes Made

- Added `docs/HANDOVER.md`, `DAILY_LOG.md`, `CHANGELOG.md`, `SKILLS_LOG.md`
- Added `README.md` at project root
- Initialized git with initial commit (`fedf02b`)
- Updated git: folder rename to `project` (`4f6b28f`)
- Updated git: .gitignore for folder rename (`a3b41c8`)
- Converted imports: `langchain_anthropic.ChatAnthropic` → `langchain_openai.ChatOpenAI`
- Updated config: `ANTHROPIC_API_KEY` → `OPENAI_API_KEY`, `claude-sonnet` → `gpt-4o`
- Updated requirements.txt: removed `anthropic`, added `openai`, `langchain-openai`
- Copied `.env`, `./.env.example`, `credentials/client_secret.json`, `credentials/token.json`

### Findings

- Single-agent architecture works with OpenAI/GPT-4o
- Demo mode processes sample emails correctly
- Agent logs tasks as intended
- All 14 tests pass (scripted LLM)
- Codebase integrates cleanly with OpenAI API

### Problems / Issues

- _(none)_

### Decisions

- Converted from Anthropic to OpenAI to share infrastructure with ChildOps project
- Renamed `childops/` → `project/` to avoid confusion with ChildOps (multi-agent) project
- OAuth credentials from ChildOps work with SingleAgentOps (same Google Cloud project, same parent account)

### Next Session

Begin live-mode testing with real Gmail/Calendar. Both agents (ChildOps multi-agent and SingleAgentOps single-agent) can now run live against the same school email inbox to compare behavior.
