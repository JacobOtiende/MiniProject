# MiniProject — Unified School Operations Agent

## Current Status

**MiniProject** is the harmonized, unified version of ChildOps (multi-agent) and SingleAgentOps (single-agent). It uses a proven single-agent architecture with an expanded tool set to handle school email triage, calendar management, task tracking, and daily briefings. The implementation is complete, tested, and ready for live-mode validation.

**Git:** Initialized and committed. Ready for deployment.

**Health:** Code is stable. 14 tests pass. Demo mode works end-to-end. OAuth credentials configured.

---

## Completed

- ✅ Single-agent architecture (agent/build_agent.py with 12 tools)
- ✅ All tool implementations (Gmail, Calendar, task log, approval queue)
- ✅ Three CLI modes: `triage`, `rundown`, `achievements`
- ✅ Demo mode with sample data (no real API calls)
- ✅ Full test suite with scripted model (tests/test_agent_loop.py)
- ✅ OAuth setup for Gmail and Google Calendar (live mode)
- ✅ System prompt with clear policy boundaries
- ✅ Comprehensive README

---

## In Progress

- 🔄 Live-mode testing (needs real Gmail/Calendar setup and test fixtures)

---

## Not Started

- ⚪ Continuous deployment / scheduling (cron / Task Scheduler)
- ⚪ Error recovery and retry logic for rate limits
- ⚪ Email read status tracking (automatic marking of processed emails as read)

---

## Blockers

**None current.** Ready to begin live-mode testing.

---

## Important Decisions

1. **Single-agent over multi-agent:** Traded the "second opinion" safety check (Control Tower) for architectural simplicity and true autonomy. Mitigated by hard boundaries: no send tool exists; all email drafts require human approval via `approvals/approval_queue.py`.

2. **Policy as instruction, not enforcement:** System prompt states behavior; nothing in code enforces it. Live testing against real inboxes is the evaluation method.

3. **Scripted tests over live tests:** Tests use a fake LLM. They prove tools work and flow correctly, not that the real model makes good choices.

---

## Known Issues

- Demo mode uses hardcoded sample emails; rerunning triage reprocesses them.
- Google OAuth token expires every 7 days in Testing mode (delete `credentials/token.json` and sign in again to refresh).
- System prompt assumes certain email formats and calendar event metadata; edge cases may confuse the agent.

---

## Immediate Next Action

1. **Initialize a git repository** at `SingleAgentOps/` (or check if childops should be a submodule / separate repo).
2. **Run demo mode to verify stability:**
   ```bash
   cd SingleAgentOps/childops
   pip install -r requirements.txt
   python main.py triage
   python main.py rundown
   python main.py achievements
   ```
3. **Set up live-mode Google Cloud credentials** (see project/README.md § "Google Cloud setup for live mode").
4. **Send test fixture emails** using `testing/send_test_email.py` to a real Gmail inbox.
5. **Run live-mode triage and record behavior** in `docs/DAILY_LOG.md`.
6. **Write up findings** in project evaluation (system prompt adherence, tool sequence quality, error handling).

---

## Recommended Next Steps

After live-mode validation:

1. Add rate-limit backoff and retry logic (like ChildOps has in agents/llm.py).
2. Implement automatic email read-status marking (requires `gmail.modify` scope expansion).
3. Add scheduled runs via cron (Linux/Mac) or Task Scheduler (Windows).
4. Consider Control Tower reintroduction if live testing reveals systematic misclassifications.

---

## Important Context

- **Why single-agent?** Simpler architecture, clearer autonomy story, easier to debug than multi-agent coordination.
- **Why not sent emails without approval?** Safety: the system can never bypass the human gate, regardless of model behavior.
- **How to evaluate quality?** Run live mode, read what the model actually does, compare against system prompt. That's the real test.
- **Relation to ChildOps project?** ChildOps (in `PROJECTS/ChildOps/`) is the multi-agent version; SingleAgentOps is an alternative design at the same stage (live testing).
