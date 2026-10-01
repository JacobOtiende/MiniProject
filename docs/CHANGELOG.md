# MiniProject — Changelog

## [2026-09-30] Observability: Logging, Token Tracking, Tool Tracing

### Added
- `project/observability/` module: RunLogger (unified logging), TokenUsageTracker (per-phase LLM cost), ToolCallTracer (tool execution metrics).
- Tool execution tracing: every tool call now records name, args, result (first 500 chars), latency (ms), error status, timestamp.
- Token usage tracking: extracts input/output tokens from LLM responses; calculates per-phase cost using GPT-4o pricing ($0.003/$0.006 per 1K tokens).
- Phase-based logging: agent loop records start/end of each phase (triage, rundown, achievements, review).
- Observability summary at run end: displays tool success rate and total token cost.
- Four output files per run: agent.log (structured logs), metrics.json (aggregated stats), tool_calls.json (detailed tool trace), tokens.json (per-phase breakdown).

### Changed
- `_report_errors()` decorator now captures execution time and logs tool calls to the RunLogger (if available in deps).
- `model.invoke` wrapped to extract token usage from response metadata.
- `main.py` initializes RunLogger at startup and passes logger to deps; displays observability summary at run end.

### Fixed
- _(none; new feature, all existing tests pass)_

### Performance
- Observability overhead: ~100-200ms per run (~1-2% impact).
- Tool tracing and token tracking are non-blocking; logging errors never interrupt tool execution or agent loop.

---

## [2026-09-29] Google Tasks, Single Command, Reliability Fixes

### Added
- Google Tasks integration (`tools/tasks_tool.py`): `log_task` adds each follow-up to the user's "My Tasks" with an agent-chosen priority label (🔴 [HIGH] / 🟠 [MEDIUM] / 🟢 [LOW]), a real due date, and the agent's one-line priority reason in the notes. Tasks are placed in due-date order (undated last) and de-duplicated by title. `mark_task_done` also completes the Google task.
- Daily summary tasks in a separate "MyAgent Daily Summary" list: ☀️ Start of day (rundown) and 🌙 End of day (wrap-up), updated in place each run.
- Sync of local tasks that never reached Google Tasks (e.g. logged while the API was unavailable).
- `mark_email_read` tool, plus an after-triage sweep that marks every school email the agent was shown as read in Gmail.
- Today's date in the system prompt, so relative dates ("this Friday") become due dates.
- `jsonstore.py`: atomic JSON saves; an unreadable file is moved aside (`*.corrupt-<time>`) instead of being overwritten.
- In-memory Google Tasks fake (`tools/demo_tasks.py`); tests grew from 14 to 24.

### Changed
- `python main.py` (no arguments) runs the whole cycle: triage → start-of-day rundown → end-of-day wrap-up → one approval review pass.
- Priority is the agent's own judgment (weighs urgency, consequences, required vs. optional, effort) instead of fixed thresholds.
- A failing tool now returns its error to the model instead of aborting the run.
- Google API clients use a fresh HTTP connection per request (thread-safe).
- OAuth: a cached token missing a newly added scope now triggers re-consent automatically. Added the `tasks` scope.
- `data/task_log.json` is no longer tracked in git (holds real school details).

### Fixed
- Approval queue could never read its own file (`json.load` after `f.read()`), so every enqueue overwrote earlier drafts and the review loop always said "All clear".
- Calendar `400 Bad Request`: naive datetimes are now sent with the local UTC offset.
- `ssl.SSLError: WRONG_VERSION_NUMBER` crash from parallel tool calls sharing one `httplib2` connection.
- `task_log.json` corruption (and silent data loss) from parallel writes: writes are now locked and atomic.

### Removed
- `run.py`, `run.bat`, `run.sh` convenience runners (replaced by plain `python main.py`).

---

## [2026-09-28] Gmail Draft Integration

### Added
- Email drafts now saved directly to Gmail drafts folder (gmail_tool.py: create_draft function)
- ApprovalQueue now accepts gmail_service and creates real Gmail drafts on enqueue

### Changed
- OAuth scopes expanded to include gmail.modify for draft creation
- ApprovalQueue stores Gmail draft ID in local queue for reference
- Red alert loop displays Gmail draft location and ID

### Fixed
- Permission scope issue: updated SCOPES in auth/google_auth.py to include gmail.modify

---

## [2026-09-28] Unified Release

### Added
- Harmonized ChildOps (multi-agent) and SingleAgentOps (single-agent) into one unified project
- Complete documentation structure: HANDOVER.md, DAILY_LOG.md, CHANGELOG.md, SKILLS_LOG.md
- Project-level README.md with architecture overview
- Git repository with full history

### Changed
- Consolidated on single-agent architecture (simpler, clearer autonomy)
- Standardized on OpenAI/GPT-4o for all inference

### Removed
- ChildOps (multi-agent version with Control Tower) — no longer maintained
- SingleAgentOps (experimental) — no longer maintained
- Multi-agent coordination logic

## [Initial Implementation]

### Added
- Single-agent architecture (agent/build_agent.py)
- 12 tools: email triage, calendar conflict detection, calendar event creation, task logging, approval queue, achievements
- Three CLI modes: triage, rundown, achievements
- Demo mode with sample email data (data/sample_emails.json)
- OAuth setup for Gmail and Google Calendar (auth/google_auth.py)
- System prompt with clear policy boundaries (agent/system_prompt.py)
- Full test suite: 14 tests with scripted LLM
- Approval gate: all drafts require human review before sending
- Config-driven settings (config.py, .env.example)
- Comprehensive README with architecture, quickstart, testing guide

### Design Decisions
- **Single-agent over multi-agent:** Removed Control Tower's second opinion in favor of architectural simplicity
- **Policy as instruction:** System prompt states behavior; not enforced in code
- **Hard safety boundary:** No send tool; approval queue requires explicit human approval outside the agent

### Known Limitations
- Demo mode reprocesses sample emails on repeated runs
- OAuth token expires every 7 days in Testing mode
- Scripted tests prove tool flow, not model judgment
